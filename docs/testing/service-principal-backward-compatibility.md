# Human-owned credential compatibility

Service principals are optional. Omitting `service_principal` during credential creation retains the existing human-owned API-token behavior, including tenant membership checks and the approved read-only scope boundary.
