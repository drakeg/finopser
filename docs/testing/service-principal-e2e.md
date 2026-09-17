# Service-principal E2E sequence

The automated acceptance test validates create → issue → authenticate → disable → reject → enable → authenticate → rotate → reject old secret → accept replacement → revoke → reject replacement. This sequence uses the local Django test database and the stable `/api/v1/` contract; it performs no live cloud calls.
