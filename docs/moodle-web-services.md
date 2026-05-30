# Moodle Web Services setup (least-privilege)

This document describes how to provision a **dedicated, least-privilege** Moodle web
service account and token for `moodle-panopto-downloader`, and how to verify it. It is
written to be reproducible for other administrators.

> The companion tool **`whisper-transcribe-de`** runs locally and uses **no** Moodle
> Web Services. Only `moodle-panopto-downloader` talks to Moodle.

## Required web service functions

The tool calls exactly the following functions (derived from the source). Each is listed
with its purpose and whether it is mandatory.

| Function | Used for | Required? |
|---|---|---|
| `core_webservice_get_site_info` | Validate the token and read the available-function list (every run starts here). | **Yes** |
| `core_course_get_contents` | Discover the Panopto links **and** derive the course vocabulary. | **Yes** |
| `mod_lti_get_ltis_by_courses` | Pick up Panopto links embedded as LTI external tools. Called only if present; the tool degrades gracefully if it is absent. | Recommended |
| `core_enrol_get_users_courses` | Only for `--all-courses` (lists the token account's own enrolled courses). | Optional |

In addition, **file download** (`<base>/webservice/pluginfile.php?...&token=<TOKEN>`) is
used by `--vocab-from-files` to read attached PDF/text materials. This is not a function;
it is enabled by the **"Can download files"** flag on the external service.

A minimal install that only needs Panopto-link discovery requires just the two **Yes**
functions; the rest are feature-dependent and can be omitted.

## Least-privilege design

- **Dedicated account** (not a reused/admin account), auth method **`webservice`**
  (fallback `manual`). Do **not** use `nologin` — Moodle denies web service access for it
  (`wsaccessusernologin`).
- **Custom role** granting only `webservice/rest:use`. No editing, no admin capabilities.
- **Scoped course access** via a normal **student enrolment** in the target course(s) —
  not a system-wide `moodle/course:view`. The token can therefore read only the courses
  the account is enrolled in.
- **Restricted external service** (`restrictedusers = 1`): only the authorised account may
  use it. `uploadfiles = 0`; `downloadfiles = 1` only because `--vocab-from-files` needs it
  (set it to `0` if that feature is not used).
- **Exactly** the functions listed above are assigned — nothing else (verified by a
  negative test: any non-assigned function is rejected).

## Setup — Option A: Moodle web interface

1. *Site administration → Server → Web services → Overview* — ensure web services and the
   **REST** protocol are enabled.
2. *Users → Add a new user*: create e.g. `ws_panopto`, auth method **Web services
   authentication** (or *Manual* with an unknown password). This account is API-only.
3. *Define roles → Add a new role* `ws_panopto_reader`, context **System**, allow only
   `webservice/rest:use`. Assign it to the account under *Assign system roles*.
4. Enrol the account as **Student** in each course whose recordings will be processed.
5. *Web services → External services → Add*: name it, set **Enabled**, **Authorised users
   only**, and **Can download files** (if using `--vocab-from-files`). Add the functions
   from the table; add the account under *Authorised users*.
6. *Manage tokens → Create token* for the account on this service. Store it securely.

## Setup — Option B: CLI script

Run on the Moodle server (adjust the variables at the top). Idempotent; touches only the
new objects:

```php
<?php
define('CLI_SCRIPT', true);
require('/path/to/moodle/config.php');           // <-- Moodle dirroot
require_once($CFG->libdir . '/externallib.php');
require_once($CFG->dirroot . '/user/lib.php');
global $DB, $CFG;

$USERNAME = 'ws_panopto';
$SERVICE_SHORT = 'panopto_dl';
$SERVICE_NAME = 'Panopto Downloader (read-only)';
$ROLE_SHORT = 'ws_panopto_reader';
$TEST_COURSE = 210;                              // <-- a course to enrol/test against
$EMAIL = 'ws-panopto@example.edu';               // <-- unique, valid format
$FUNCS = [
    'core_webservice_get_site_info',
    'core_course_get_contents',
    'mod_lti_get_ltis_by_courses',
    'core_enrol_get_users_courses',
];

// Account — web-service auth (NOT 'nologin'); fall back to 'manual'.
$enabled = array_filter(explode(',', (string) ($CFG->auth ?? '')));
$auth = in_array('webservice', $enabled, true) ? 'webservice' : 'manual';
$user = $DB->get_record('user', ['username' => $USERNAME]);
if (!$user) {
    $u = (object) [
        'auth' => $auth, 'confirmed' => 1, 'mnethostid' => $CFG->mnet_localhost_id,
        'username' => $USERNAME, 'firstname' => 'WS', 'lastname' => 'Panopto Downloader',
        'email' => $EMAIL, 'policyagreed' => 1,
    ];
    $user = $DB->get_record('user', ['id' => user_create_user($u, false, false)]);
}

// Minimal role at system context: only webservice/rest:use.
$roleid = $DB->get_field('role', 'id', ['shortname' => $ROLE_SHORT])
    ?: create_role('Web Service – Panopto Downloader (read-only)', $ROLE_SHORT, '');
set_role_contextlevels($roleid, [CONTEXT_SYSTEM]);
$sysctx = context_system::instance();
assign_capability('webservice/rest:use', CAP_ALLOW, $roleid, $sysctx->id, true);
$sysctx->mark_dirty();
role_assign($roleid, $user->id, $sysctx->id);

// Scope course access via a student enrolment in the target course.
$studentrole = $DB->get_field('role', 'id', ['shortname' => 'student']);
$instance = $DB->get_record('enrol', ['courseid' => $TEST_COURSE, 'enrol' => 'manual']);
if ($instance && $studentrole) {
    enrol_get_plugin('manual')->enrol_user($instance, $user->id, $studentrole);
}

// Restricted service with downloadfiles + exactly the needed functions.
$svc = $DB->get_record('external_services', ['shortname' => $SERVICE_SHORT]);
if (!$svc) {
    $svc = (object) [
        'name' => $SERVICE_NAME, 'shortname' => $SERVICE_SHORT, 'enabled' => 1,
        'restrictedusers' => 1, 'downloadfiles' => 1, 'uploadfiles' => 0,
        'timecreated' => time(), 'timemodified' => time(),
    ];
    $svc->id = $DB->insert_record('external_services', $svc);
}
foreach ($FUNCS as $fn) {
    $c = ['externalserviceid' => $svc->id, 'functionname' => $fn];
    if (!$DB->record_exists('external_services_functions', $c)) {
        $DB->insert_record('external_services_functions', (object) $c);
    }
}
$uc = ['externalserviceid' => $svc->id, 'userid' => $user->id];
if (!$DB->record_exists('external_services_users', $uc)) {
    $DB->insert_record('external_services_users', (object) ($uc + ['timecreated' => time()]));
}

// Token (reuse a valid one, else mint).
$token = null;
foreach ($DB->get_records('external_tokens', $uc) as $t) {
    if (empty($t->validuntil) || $t->validuntil > time()) { $token = $t->token; }
}
if (!$token) {
    $perm = defined('EXTERNAL_TOKEN_PERMANENT') ? EXTERNAL_TOKEN_PERMANENT : 0;
    $token = \core_external\util::generate_token($perm, $svc, $user->id, $sysctx);
}
echo "TOKEN\t$token\n";
```

## Token handling

- Treat the token like a password. Store it outside version control (env `MOODLE_TOKEN`,
  a `--token-file`, or a file with `chmod 600`).
- The token is bound to the dedicated account and the restricted service only.
- Revoke it any time under *Manage tokens* (or delete the account/service to remove all
  access). Production tokens of other accounts are unaffected by this setup.

## Verification

Replace `BASE` and `TOKEN`. Each call should return data, not an `exception`.

```bash
BASE="https://moodle.example.edu"; TOKEN="xxxxxxxx"
api() { curl -s "$BASE/webservice/rest/server.php" \
  --data-urlencode "wstoken=$TOKEN" --data "moodlewsrestformat=json" \
  --data "wsfunction=$1" "${@:2}"; }

api core_webservice_get_site_info                       # lists exactly the 4 functions
api core_course_get_contents      --data "courseid=210"
api mod_lti_get_ltis_by_courses   --data "courseids[0]=210"
api core_enrol_get_users_courses  --data "userid=<this-account-userid>"

# Negative test (must be rejected — function not in the service):
api core_user_get_users_by_field  --data "field=id" --data "values[0]=2"
```

End-to-end with the tool:

```bash
moodle-panopto-downloader 210 --list --base-url "$BASE" --token-file token.txt
moodle-panopto-downloader 210 --write-vocab vocab.txt --vocab-from-files \
  --base-url "$BASE" --token-file token.txt
moodle-panopto-downloader --all-courses --list --base-url "$BASE" --token-file token.txt
```

### Reference test results (Moodle 5.1.3, course 210)

| Test | Result |
|---|---|
| `core_webservice_get_site_info` | PASS — token exposes exactly the 4 functions, `downloadfiles=1` |
| `core_course_get_contents` | PASS — 32 sections, 102 modules |
| `mod_lti_get_ltis_by_courses` | PASS |
| `core_enrol_get_users_courses` | PASS — own courses `[210]` |
| Negative test (unassigned function) | PASS — correctly rejected |
| Tool `--list` | PASS — 11 Panopto URLs |
| Tool `--write-vocab --vocab-from-files` | PASS — 34 files read, 250 terms |
| Tool `--all-courses` | PASS — processes course 210 |

## Reducing permissions further

- Drop `core_enrol_get_users_courses` if `--all-courses` is not used.
- Drop `mod_lti_get_ltis_by_courses` if no Panopto videos are embedded as LTI tools.
- Set the service's `downloadfiles = 0` if `--vocab-from-files` is not used.
- The role already holds only `webservice/rest:use`; course access is the single student
  enrolment — nothing further to remove.

## Teardown

Remove cleanly by deleting, in this order: the token, the external service, the role
assignment and role, the course enrolment, and the user account. Nothing outside these
objects is affected.
