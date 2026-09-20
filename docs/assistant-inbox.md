# Assistant Inbox

Workbench checks for unapproved external proposals across every case about every two seconds while the app is open and idle. It shows waiting proposals on startup and alerts once per new proposal in the current session. Inbox does not run checks or alter editor contents. Current, stale, and revoked proposals stay distinguishable. The current preview bounds the inbox to the latest 500 submissions; its notice reports that cutoff.

Review selects an exact case and proposal independently of the editor's folder. Its original content hash, current revision, host access, saved snapshot, and one-time approval remain enforced by the desktop approval service. Completed results refresh the review and remove the proposal from the pending Inbox. Unchanged polls produce no repeated popup and no repeated activity entry.

The Inbox source is the shared workflow database. Diagnostics include a persistent workspace identifier and, on Windows, the physical opened database path. This helps distinguish packaged-app AppData redirection from a true connector mismatch without changing configuration or migrating data. These physical paths stay in local technical diagnostics.

Run the native `--inbox-ui-smoke` test for a real MCP stdio submission from another process while a different case has unsaved edits. It verifies automatic delivery, notification suppression, exact review, no run before approval, approved result, Inbox removal, replay prevention, and editor preservation. All data is temporary. Optional `--capture-inbox PATH` and `--capture PATH` save test screenshots.
