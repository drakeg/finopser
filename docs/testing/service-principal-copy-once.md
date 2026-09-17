# Copy-once credential behavior

API credential creation and rotation return plaintext only in that response. The Administration workspace holds that value only in transient page state so it can be copied, and clears it when dismissed or when the Administration workspace is left. Token listings contain metadata and prefixes only; they cannot recover a previous plaintext secret.
