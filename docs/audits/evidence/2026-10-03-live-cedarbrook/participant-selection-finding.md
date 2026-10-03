# Participant selection finding

The real source graph contains seven entities in insertion order: Cedarbrook, Maya Chen, Leo Martin, Priya Shah, Daniel Brooks, Main Street, City of Cedarbrook. The UI exposed only an agent cap. With the planned empty type filter and cap four, preparation would select Cedarbrook and omit Daniel. This was found before any persona generation. The workflow was manually stopped with two measured real requests and no in-flight request.

Two component regressions failed before the repair. A native multiple selector now submits and restores the existing supported entity_types_include setting. Selecting Resident, ShopOwner and TransportPlanner yields exactly the four named source participants before applying the cap. The original frozen input and planned settings are retained; effective-settings-corrected.json records this additional filter.

Verification: 12 Node tests, 39 component tests, build, 10 existing backend contract/manager tests; actual source entity-filter endpoint returned all four named people. No model output was substituted or seeded.
