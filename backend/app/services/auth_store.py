"""Durable invitation and revocable browser-session state for the OIDC boundary."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import secrets
import sqlite3
import time


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class AuthStore:
    def __init__(self, path, issuer, admin_email):
        self.path, self.issuer, self.admin_email = path, issuer, admin_email.lower()
        new_file = not Path(path).exists()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS auth_users (
                    id TEXT PRIMARY KEY, issuer TEXT NOT NULL, subject TEXT NOT NULL,
                    email TEXT NOT NULL, role TEXT NOT NULL, suspended INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(issuer, subject), UNIQUE(email));
                CREATE TABLE IF NOT EXISTS auth_invites (
                    token_hash TEXT PRIMARY KEY, email TEXT NOT NULL, expires REAL NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0, creator TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, csrf TEXT NOT NULL,
                    expires REAL NOT NULL, touched REAL NOT NULL);
            ''')

        if new_file:
            Path(path).chmod(0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def invite(self, email, creator):
        email = email.strip().lower()
        if len(email) > 254 or '@' not in email or any(c.isspace() for c in email):
            raise ValueError('Enter a valid email address.')
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute('DELETE FROM auth_invites WHERE email=? OR expires<?', (email, time.time()))
            db.execute('INSERT INTO auth_invites VALUES (?, ?, ?, 0, ?)',
                       (digest(token), email, time.time() + 86400, creator))
        return token

    def admit(self, claims, invitation):
        email = claims.get('email', '')
        subject = claims.get('sub')
        if (claims.get('iss') != self.issuer or not isinstance(subject, str) or not subject
                or not isinstance(email, str) or not email or claims.get('email_verified') is not True):
            raise ValueError('A verified identity and email are required.')
        email = email.lower()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            user = db.execute('SELECT * FROM auth_users WHERE issuer=? AND subject=?',
                              (self.issuer, subject)).fetchone()
            if user:
                if user['suspended'] or user['email'] != email:
                    raise ValueError('Account unavailable; contact the operator.')
            else:
                role = 'tester'
                if email == self.admin_email and not db.execute("SELECT 1 FROM auth_users WHERE role='admin'").fetchone():
                    role = 'admin'
                else:
                    invite = db.execute('SELECT * FROM auth_invites WHERE token_hash=?',
                                        (digest(invitation or ''),)).fetchone()
                    if not invite or invite['used'] or invite['expires'] <= time.time() or invite['email'] != email:
                        raise ValueError('An unused, unexpired invitation for this email is required.')
                    db.execute('UPDATE auth_invites SET used=1 WHERE token_hash=?', (digest(invitation),))
                if role == 'admin' and not (isinstance(claims.get('amr'), list) and 'mfa' in claims['amr']):
                    raise ValueError('Administrator sign-in requires provider-verified MFA.')
                identifier = secrets.token_hex(16)
                try:
                    db.execute('INSERT INTO auth_users VALUES (?, ?, ?, ?, ?, 0)',
                               (identifier, self.issuer, subject, email, role))
                except sqlite3.IntegrityError:
                    raise ValueError('Identity cannot be linked automatically; contact the operator.') from None
                user = db.execute('SELECT * FROM auth_users WHERE id=?', (identifier,)).fetchone()
            if user['role'] == 'admin' and not (isinstance(claims.get('amr'), list) and 'mfa' in claims['amr']):
                raise ValueError('Administrator sign-in requires provider-verified MFA.')
            return dict(user)

    def new_session(self, user_id):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = time.time()
        with self.db() as db:
            db.execute('DELETE FROM auth_sessions WHERE expires<? OR touched<?', (now, now-1800))
            db.execute('INSERT INTO auth_sessions VALUES (?, ?, ?, ?, ?)',
                       (digest(token), user_id, csrf, now+28800, now))
        return token, csrf

    def session(self, token):
        now = time.time()
        with self.db() as db:
            row = db.execute('''SELECT u.*, s.csrf FROM auth_sessions s JOIN auth_users u ON u.id=s.user_id
                WHERE s.token_hash=? AND s.expires>? AND s.touched>? AND u.suspended=0''',
                (digest(token), now, now-1800)).fetchone()
            if row:
                db.execute('UPDATE auth_sessions SET touched=? WHERE token_hash=?', (now, digest(token)))
                return dict(row)

    def revoke(self, token):
        with self.db() as db:
            db.execute('DELETE FROM auth_sessions WHERE token_hash=?', (digest(token),))

    def revoke_all(self, user_id):
        with self.db() as db:
            db.execute('DELETE FROM auth_sessions WHERE user_id=?', (user_id,))

    def suspend(self, user_id, suspended, actor):
        if user_id == actor:
            raise ValueError('You cannot suspend your own administrator account.')
        with self.db() as db:
            db.execute('UPDATE auth_users SET suspended=? WHERE id=? AND role=?',
                       (int(suspended), user_id, 'tester'))
            db.execute('DELETE FROM auth_sessions WHERE user_id=?', (user_id,))

    def accounts(self):
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT id,email,role,suspended FROM auth_users ORDER BY email')]
