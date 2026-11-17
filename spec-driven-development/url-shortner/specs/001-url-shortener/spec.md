# Feature Specification: URL Shortener

**Feature Branch**: `001-url-shortener`

**Created**: 2026-11-17

**Status**: Draft

**Input**: User description: "Build url link shortening application. A signed-in user submits
a long web address and gets a short link with a random 7-character code. Codes are never
reused, even after a link is deleted. Anyone who opens a short link is sent to the original
address. A user can set an expiry date; after it, the link shows a "link expired" page instead
of redirecting. A user can disable a link and enable it again. Every redirect counts as a
click, and owners see total clicks and clicks per day for the last 30 days. Users only see and
manage their own links. 95% of redirects must complete within 50 ms with 1 million stored
links."

## Clarifications

### Session 2026-11-17

- Q: How should users sign in to the URL shortener? → A: Email and password accounts built
  into the app; no password reset or email verification in this version.
- Q: Should the service limit how many links one user can create, to stop abuse? → A: Each
  user can create at most 100 links per rolling hour; over the limit, a plain message says
  when they can try again. No malicious-site checking.
- Q: How much traffic must the service handle while still finishing 95% of redirects within
  50 ms? → A: 50 redirects per second sustained.
- Q: Which time zone should decide where one day ends and the next begins in the "clicks
  per day" view? → A: The link owner's time zone, detected from their browser at sign-up and
  sign-in and saved on their account (revised during planning so clicks can be stored as one
  row per link per day).
- Q: If a click can't be recorded at the moment someone opens a short link, should the
  visitor still be redirected? → A: Always redirect; log the recording failure and allow
  that click to be missed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Shorten a link and share it (Priority: P1)

A signed-in user pastes a long web address, submits it, and immediately gets a short link
made of the service address plus a random 7-character code. They copy the short link and
share it. Anyone who opens the short link — signed in or not — lands on the original address.

**Why this priority**: This is the whole reason the product exists. Without it, nothing else
has value.

**Independent Test**: Sign in, submit a long address, open the returned short link in a
private browser window, and confirm it arrives at the original address.

**Acceptance Scenarios**:

1. **Given** a signed-in user, **When** they submit `https://example.com/a/very/long/path?x=1`,
   **Then** they see a short link whose code is exactly 7 characters and a one-click way to
   copy it.
2. **Given** an existing active short link, **When** anyone opens it, **Then** they are sent
   to the original address.
3. **Given** a signed-in user, **When** they submit text that is not a valid http or https web
   address, **Then** no link is created and they see a message saying what is wrong.
4. **Given** a visitor who is not signed in, **When** they try to create a short link,
   **Then** they are asked to sign in first.
5. **Given** a user submits the same long address twice, **When** both submissions succeed,
   **Then** each gets its own distinct code.
6. **Given** someone opens a short link whose code never existed or was deleted, **When** the
   page loads, **Then** they see a "link not found" page.

---

### User Story 2 - Manage my own links (Priority: P2)

A signed-in user sees a list of the links they created, with the original address, the short
link, its status (active, disabled, expired), and its expiry date if set. They can disable a
link so it stops redirecting, enable it again, and delete links they no longer want. They
never see or affect anyone else's links.

**Why this priority**: Once people create links, they need control over them. Ownership
isolation is a privacy requirement.

**Independent Test**: With two accounts, create links in each; confirm each account lists
only its own links, and that disabling, enabling, and deleting work and affect redirects
as expected.

**Acceptance Scenarios**:

1. **Given** a user with three links, **When** they open their link list, **Then** they see
   exactly those three links, newest first.
2. **Given** an active link, **When** the owner disables it, **Then** anyone opening it sees a
   "link disabled" page instead of being redirected.
3. **Given** a disabled link, **When** the owner enables it, **Then** opening it redirects
   again.
4. **Given** a link, **When** the owner deletes it, **Then** it disappears from their list,
   opening it shows "link not found", and its code is never assigned to any future link.
5. **Given** user A and user B, **When** user B tries to view, change, or delete user A's link
   by any means, **Then** the attempt fails and reveals nothing about user A's link.

---

### User Story 3 - Set an expiry date (Priority: P3)

When creating a link, or later, the owner can set an expiry date and time. After that moment
the short link shows a "link expired" page instead of redirecting. The owner can change or
remove the expiry.

**Why this priority**: Useful for time-limited campaigns, but the product works without it.

**Independent Test**: Create a link with an expiry a few minutes ahead; confirm it redirects
before and shows "link expired" after.

**Acceptance Scenarios**:

1. **Given** a link with an expiry in the future, **When** someone opens it before the expiry,
   **Then** they are redirected.
2. **Given** a link whose expiry has passed, **When** someone opens it, **Then** they see a
   "link expired" page and are not redirected.
3. **Given** a user setting an expiry, **When** they choose a moment in the past, **Then** the
   change is rejected with a clear message.
4. **Given** an expired link, **When** the owner sets a new future expiry or removes the
   expiry, **Then** the link redirects again (unless it is disabled).

---

### User Story 4 - See how my links perform (Priority: P4)

The owner of a link sees its total number of clicks and a day-by-day count for the last 30
days, including days with zero clicks.

**Why this priority**: Valuable insight, but depends on links already being created and
shared.

**Independent Test**: Open a short link a known number of times; confirm the total and
today's count increase by exactly that number.

**Acceptance Scenarios**:

1. **Given** a link opened 5 times today and 3 times yesterday, **When** the owner views its
   statistics, **Then** they see a total of 8, 5 for today, 3 for yesterday, and 0 for each
   other day in the 30-day window.
2. **Given** a link that is disabled, expired, or deleted, **When** someone opens it, **Then**
   no click is counted.
3. **Given** a link created 10 days ago, **When** the owner views statistics, **Then** the
   30-day view still shows 30 days, with zeros before the creation date.

---

### Edge Cases

- Submitted address is longer than 2,048 characters → rejected with a message.
- Submitted address points to this shortener's own short links → rejected, to prevent
  redirect loops.
- A link is both disabled and expired → visitors see "link disabled" (the owner's explicit
  choice wins).
- Short codes are case-sensitive; opening a code with different letter case is treated as a
  different code.
- A randomly generated code collides with any code ever issued (including deleted ones) → a
  new code is generated; the user never sees an error for this.
- A user submits their 101st link within 60 minutes → it is refused with a message giving
  the time they can try again; deleting links does not free up the hourly allowance.
- Two visitors open the same link at the same instant → both clicks are counted.
- The owner signs in from a browser in a new time zone → their saved time zone is updated;
  clicks from then on are grouped by the new zone's days, while days already recorded keep
  the zone they were recorded in.
- Recording a click fails during a visit → the visitor is still redirected; the failure is
  logged and the click may be missing from statistics.
- Deleting a link also removes its click statistics.
- A signed-in user's session ends while managing links → they are asked to sign in again
  without losing context of where they were.

## Requirements *(mandatory)*

### Functional Requirements

**Accounts & ownership**

- **FR-001**: System MUST let people create an account and sign in with an email address and
  password built into the app, and sign out. Email addresses MUST be unique per account.
  No outside sign-in provider, password reset, or email verification is provided.
- **FR-002**: System MUST require sign-in to create, list, change, delete, or view statistics
  for links.
- **FR-003**: System MUST show and allow changes to a link only for its owner; requests for
  another user's link MUST behave exactly as if the link does not exist.

**Creating links**

- **FR-004**: System MUST accept only absolute `http` or `https` addresses up to 2,048
  characters and MUST reject addresses that point to the shortener itself.
- **FR-005**: System MUST assign each new link a randomly generated 7-character code using
  upper-case letters, lower-case letters, and digits.
- **FR-006**: System MUST NOT assign a code that has ever been issued before, including codes
  of deleted links.
- **FR-007**: System MUST show the full short link after creation with a one-click copy
  action and visible confirmation that it was copied.
- **FR-007a**: System MUST limit each user to at most 100 link creations in any rolling
  60-minute window. A request over the limit MUST create no link and MUST show a plain
  message stating when the user can create links again. Submitted addresses are not
  checked against malicious-site lists.
- **FR-008**: Users MAY set an optional expiry date and time when creating a link; it MUST be
  in the future.

**Redirecting**

- **FR-009**: Opening the short link of an active, unexpired link MUST send the visitor to the
  original address, without requiring sign-in.
- **FR-010**: Opening a link after its expiry MUST show a "link expired" page and MUST NOT
  redirect.
- **FR-011**: Opening a disabled link MUST show a "link disabled" page and MUST NOT redirect.
- **FR-012**: Opening an unknown or deleted code MUST show a "link not found" page.
- **FR-013**: Redirects MUST be signalled as temporary so that browsers check with the service
  on every visit and each visit can be counted.

**Managing links**

- **FR-014**: Owners MUST be able to list their links, newest first, showing original address,
  short link, status (active / disabled / expired), expiry, creation date, and total clicks.
- **FR-015**: Owners MUST be able to disable and re-enable a link.
- **FR-016**: Owners MUST be able to set, change, or remove a link's expiry.
- **FR-017**: Owners MUST be able to delete a link, after confirming the action; deletion is
  permanent and removes its statistics.

**Statistics**

- **FR-018**: Every successful redirect MUST count as exactly one click; visits that do not
  redirect MUST NOT be counted.
- **FR-018a**: A failure to record a click MUST NOT prevent or delay the redirect; the
  visitor is still sent to the original address, the failure MUST be logged, and that click
  MAY be missing from statistics.
- **FR-019**: Owners MUST be able to see a link's all-time total clicks and a click count for
  each of the last 30 calendar days (today included), with zero for days without clicks.
  Day boundaries MUST follow the owner's saved time zone, which is detected from the owner's
  browser at sign-up and sign-in; if it cannot be detected, UTC is used. The statistics view
  MUST state which time zone the days are shown in.
- **FR-020**: Click counts MUST be reflected in statistics within 1 minute of the redirect.

**Interface**

- **FR-021**: All pages MUST follow the project constitution's Usability (III) and
  Human-Crafted Interface (V) principles: plain language, specific error messages,
  keyboard-operable, usable at phone width.

### Key Entities

- **User**: A person with an account. Has an email address, a password, and a saved time zone
  (detected from their browser at sign-up and sign-in; used for clicks per day); owns zero or more
  links.
- **Link**: A shortened address. Has a unique 7-character code, the original address, its
  owner, creation time, optional expiry time, and an enabled/disabled flag. Status is derived:
  disabled, else expired, else active.
- **Issued Code**: The permanent record that a code has been used; outlives the link so the
  code is never reissued.
- **Click**: One successful redirect of a link at a moment in time; aggregated into a total and
  daily counts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With 1 million links stored and a sustained load of 50 redirects per second,
  95% of redirects complete within 50 ms, measured from the service receiving the request
  to it sending the response (network time to the visitor excluded).
- **SC-002**: A signed-in user can go from pasting a long address to having the short link
  copied in under 10 seconds.
- **SC-003**: Across all links ever created, zero codes are issued more than once.
- **SC-004**: When click recording is working normally, click totals match the number of
  successful redirects with 100% accuracy in controlled tests; every missed click is
  accounted for by a logged recording failure.
- **SC-005**: In testing, no user can see or change any link they do not own (0 successful
  cross-account accesses).
- **SC-006**: 9 out of 10 first-time users create and copy a short link without help.

## Assumptions

- Sign-in uses a simple email + password account built into the product. Password reset,
  email verification, social login, and teams are out of scope for this version.
- Every successful redirect counts, including repeat visits and automated visitors; no bot
  filtering or unique-visitor counting.
- The original address of a link cannot be edited after creation (create a new link
  instead).
- Custom (user-chosen) codes, QR codes, bulk creation, and a public API are out of scope.
- Expiry is checked at the moment of each visit; no notification is sent when a link expires.
- The 7-character code space (62⁷ ≈ 3.5 trillion) is large enough that never reusing codes is
  not a practical limit.
