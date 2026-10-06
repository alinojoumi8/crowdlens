# Report and proposal review UI

Completed the approved follow-up UI pass.

| Area | Before | After |
| --- | --- | --- |
| Report reading | Narrow fixed report panel and no reading guide | Report gets 64% of desktop space; narrow screens stack panels; reading guide explains review sequence |
| Proposal review | Comparison, claims, and saving lacked a shared sequence | Three numbered review steps with clearer summary/source labels |
| Save availability | Disabled save button without a reason | Visible, accessible guidance for preparing, blocked, stale, failed, and saved proposals |
| Report tools | Recovery and regeneration buttons always exposed | Expandable tools panel explains linked-resource requirements and regeneration |
| Interaction | Smaller button targets | Minimum 44px button targets and focus indicators |

Approval, authorization, generation, source validation, persistence, and revision logic remain unchanged. Existing report content is preserved. The report tag now says Scenario Analysis Report where it previously said Prediction Report; structured forecast fields remain intact.

Validation: all 12 Node and 54 component tests passed; production build and diff whitespace checks passed. Browser checked the recorded ready fictional Fernbank proposal at desktop and 390 x 844 mobile dimensions; no mobile page overflow. Comparison and recovery disclosures were inspected. No proposal was accepted, rejected, or regenerated. The read-only preview blocks mutations and provider calls. Temporary viewport override was reset.

Review preview: http://127.0.0.1:18812/report/report_completion_dev_repair?proposal=proposal_28dfbab0b8ba4d9785fd4c3529dc88a0&section=1
