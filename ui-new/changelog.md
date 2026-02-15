# ui-new Changelog

## 2026-02-15
- Prompt: Nav links font size still not visible.
- Changes:
  - Navbar: Use Tailwind text-xl instead of Mantine size prop.
- Notes: none

## 2026-02-15
- Prompt: Nav links font size increase not visible.
- Changes:
  - Navbar: Nav links size="lg" → size="xl" for more noticeable increase.
- Notes: none

## 2026-02-15
- Prompt: Nav links font size +1 point.
- Changes:
  - Navbar: Nav links size="md" → size="lg".
- Notes: none

## 2026-02-15
- Prompt: Remove underline from nav links (still showing).
- Changes:
  - Navbar: Anchor underline="never" to disable default underline.
- Notes: none

## 2026-02-15
- Prompt: Hover effect not underline but color white.
- Changes:
  - Navbar: Nav links remove underline, add hover:text-white.
- Notes: none

## 2026-02-15
- Prompt: Space from logo.
- Changes:
  - Navbar: Left group gap="lg" → gap="xl" (more space between logo, links, burger).
- Notes: none

## 2026-02-15
- Prompt: Hover effect on nav links.
- Changes:
  - Navbar: Nav links use Anchor with underline="hover" inherit.
- Notes: none

## 2026-02-15
- Prompt: Nav links space 2 more points.
- Changes:
  - Navbar: Nav links Group gap="md" → gap="xl".
- Notes: none

## 2026-02-15
- Prompt: Nav links space 2 more points.
- Changes:
  - Navbar: Nav links Group gap="sm" → gap="md".
- Notes: none

## 2026-02-15
- Prompt: Make space between nav links bigger by 1 point.
- Changes:
  - Navbar: Nav links Group gap="xs" → gap="sm".
- Notes: none

## 2026-02-15
- Prompt: Make nav links font size bigger by 1 point.
- Changes:
  - Navbar: Nav links Text size="sm" → size="md".
- Notes: none

## 2026-02-15
- Prompt: Burger should match other dropdown buttons.
- Changes:
  - Navbar: Burger button reverted to variant="light", removed scale (matches Top Up, User).
- Notes: none

## 2026-02-15
- Prompt: Remove bg for burger button, make it 25% bigger.
- Changes:
  - Navbar: Burger button variant="subtle" (no background), scale-[1.25].
- Notes: none

## 2026-02-15
- Prompt: Make burger button smaller by 50%.
- Changes:
  - Navbar: Burger button uses scale-50 for 50% visual reduction.
- Notes: none

## 2026-02-15
- Prompt: Burger icon same as other dropdown buttons (black background), right of links.
- Changes:
  - Navbar: Burger menu now uses Button variant="light" (matches Top Up, User), moved to left group right after nav links.
- Notes: none

## 2026-02-15
- Prompt: Navbar links, burger menu, profile tabs, empty placeholder pages.
- Changes:
  - Navbar: Added nav links (Home, Transactions, Invoices, Deposits, Fee, Split, Exchange, Stats, Users), Burger menu with Treasuries/Tags dropdown, replaced inline styles with Mantine/Tailwind.
  - Profile: Added Tabs (Profile / Statistics) with URL search param ?tab=profile|statistics.
  - App.tsx: Added routes for transactions, invoices, deposits, fee, splits, exchange, stats, users, treasuries, tags.
  - pages/: Created empty placeholder pages (Transactions, Invoices, Deposits, Fee, Splits, Exchange, Stats, Users, Treasuries, Tags) with page name text only.
- Notes: none

## 2026-02-15
- Prompt: Update gitignore to really ignore all kinds of shit files.
- Changes:
  - Root .gitignore: Expanded with OS junk (.DS_Store, Thumbs.db, etc.), IDEs (.idea, .vscode, swap files), Python cache/coverage, Node build artifacts, logs, secrets, backups.
- Notes: none

## 2026-02-15
- Prompt: Remove inline styles, add no-inline-styles rule.
- Changes:
  - Profile.tsx: Replaced all `style={{}}` with Mantine props (`lh`) and Tailwind `className`.
  - .cursor/rules/ui-new-architecture.mdc: Added rule "Never use inline style={{}}. Use Mantine style props, className with Tailwind, or CSS modules."
- Notes: none

## 2026-02-15
- Prompt: Username and "This is you" badge vertical alignment fix.
- Changes:
  - Profile.tsx: Switched to Flex with align="center", added marginTop: 1 on Badge to optically align with username.
- Notes: none

## 2026-02-15
- Prompt: Implement plan - Profile by ID and clickable usernames.
- Changes:
  - entities.ts: getEntity(id) already present.
  - App.tsx: route profile/:id? already present.
  - Profile.tsx: EntityLink switched to Mantine Anchor with underline="hover" and inherit for same-color-as-text styling.
  - Navbar: Profile link to /profile/{actorEntity.id} already present.
- Notes: Plan items were largely implemented; refined EntityLink per plan spec (underline on hover).

## 2026-02-15
- Prompt: Username and "This is you" badge vertical alignment.
- Changes:
  - Profile.tsx: Group with align="center", lineHeight: 1 on Text and Badge, flexShrink: 0 on Badge for consistent vertical centering.
- Notes: none

## 2026-02-15
- Prompt: Profile by ID and clickable usernames - view any entity, "This is you" badge, links in tables.
- Changes:
  - api/entities.ts: added getEntity(id).
  - App.tsx: route profile/:id? (optional param).
  - Profile.tsx: useParams id, fetch by id, redirect /profile to /profile/{myId}, "This is you" badge when own profile, hide auth for others, EntityLink for From/To/Actor in tables.
  - Navbar: Profile link to /profile/{actorEntity.id}.
- Notes: none

## 2026-02-15
- Prompt: Simplify TagList - use boolean showAll instead of maxVisible.
- Changes:
  - TagList: replaced `maxVisible` with `showAll` boolean; `showAll` = all tags, default = 3 + overflow.
- Notes: none

## 2026-02-15
- Prompt: Profile - show all tags in profile card, hide overflow only in tables.
- Changes:
  - TagList: added boolean `showAll` prop; when true show all tags, when false (default) show 3 + +N overflow.
  - Profile card: `TagList tags={e.tags} showAll` so all entity tags are visible.
- Notes: none

## 2026-02-15
- Prompt: Fix "By card" redirecting to /top-up/card instead of opening modal in place.
- Changes:
  - Extracted `CardTopUpModal` from `CardTopUp` with `opened`/`onClose` props in `ui-new/src/pages/TopUp/Card/CardTopUp.tsx`.
  - Navbar: "By card" now opens modal via `useDisclosure` instead of `Link`; `CardTopUpModal` rendered in Navbar.
  - Kept `/top-up/card` route for direct URL access (still shows modal, closes to home).
- Notes: none

## 2026-02-15
- Prompt: Tone down confetti - less intense.
- Changes:
  - Reduced `fireConfetti` from 5 waves to 3 (center burst, side cannons, short rain). Halved particle counts, shortened rain from 2s to 1.2s, removed star shower and final side burst.
- Notes: none

## 2026-02-15
- Prompt: Fix confetti firing twice (on completion and again on OK click).
- Changes:
  - Added `successFired` ref in `src/pages/DepositDetail/DepositDetail.tsx` to guard the success effect so confetti only fires once per deposit. Removed `successOpen` from the dependency array.
- Notes: The old guard used `successOpen` state which reset to `false` on OK, re-triggering the effect.

## 2026-02-15
- Prompt: Make confetti animation much more impressive to encourage donations.
- Changes:
  - Rewrote `fireConfetti` in `src/pages/DepositDetail/DepositDetail.tsx` with five staggered waves: big center burst, side cannons from both edges, star-shaped shower, continuous gentle rain for ~2 seconds, and a final side burst.
  - Added gold/green/orange/purple color palette and mixed shapes (stars, default).
- Notes: Uses only canvas-confetti; no new dependencies.

## 2026-02-15
- Prompt: Fix deposit mock success (dev mode) - error handling and manual complete.
- Changes:
  - Updated `src/pages/DepositDetail/DepositDetail.tsx`: added error state and `.catch()` for `completeDepositDev`, Alert on failure with Retry button, manual "Complete now (dev)" button for dev deposits.
  - Updated `api/app/routes/deposits.py`: improved error messages for 403/400 (dev mode not enabled, not a dev deposit, deposit belongs to another entity).
- Notes: Dev deposits now surface API errors instead of failing silently; users can retry or trigger completion manually.

## 2026-02-15
- Prompt: Fix deposit dev complete still failing with "Must be a pending Keepz deposit".
- Changes:
  - Fixed `api/app/routes/deposits.py`: changed `deposit.status != "pending"` to `deposit.status != DepositStatus.PENDING`. The status field is a `DepositStatus` enum, so comparing with a plain string always fails.
- Notes: This was the actual root cause. The enum-to-string comparison (`DepositStatus.PENDING != "pending"`) is always `True` in Python, causing the endpoint to reject every request.

## 2026-02-13 00:25
- Prompt: Bootstrap changelog tracking and architecture guidance rules for Cursor.
- Changes:
  - Added `.cursor/rules/ui-new-changelog.mdc` to require appending changelog entries.
  - Added `.cursor/rules/ui-new-architecture.mdc` with ui-new architecture constraints.
  - Created `ui-new/changelog.md` as the canonical running log.
- Notes: Architecture rules scoped to `ui-new/**` only.

## 2026-02-14 03:19
- Prompt: Explain how to run and access the new frontend locally.
- Changes:
  - Provided local run commands for backend and `ui-new` Vite app.
  - Documented access URLs for new and legacy frontends.
- Notes: Docs/Guidance only.

## 2026-02-14 04:47
- Prompt: Implement modern SignIn page with Mantine, Zod, and React Hook Form.
- Changes:
  - Created `src/pages/SignIn/SignIn.tsx` with tabs for "Request Link" and "Enter Token".
  - Created `src/components/SignInForm/SignInForm.tsx` for username-based login flow.
  - Added `src/api/auth.ts` for `requestToken` API call.
  - Updated `src/App.tsx` with `Routes`, `Route`, and `ProtectedRoute`/`PublicRoute` guards.
- Notes: Replaced simple LoginCard with a full-page auth experience. Kept "Enter Token" as a fallback tab.

## 2026-02-14 04:52
- Prompt: Refine SignIn page: remove "Enter Token", simplify layout, move branding.
- Changes:
  - Removed `src/components/LoginCard` component and directory.
  - Updated `src/pages/SignIn/SignIn.tsx` to remove tabs and move "Refinance" title to top-left.
  - Simplified `SignIn` page to only show `SignInForm`.
- Notes: Removed "Enter Token" functionality from UI as requested.

## 2026-02-14 04:53
- Prompt: Update Makefile to run both legacy and new UI with `make dev`.
- Changes:
  - Updated `Makefile` to run `ui-new` dev server in parallel with docker-compose.
- Notes: Uses `&` to run in background, might be messy with logs but fulfills request.

## 2026-02-14 05:04
- Prompt: Fix login redirect to point to ui-new (port 5173) instead of legacy UI.
- Changes:
  - Created `src/pages/AuthCallback/AuthCallback.tsx` to handle `/auth/token/:token` route.
  - Updated `src/App.tsx` to add the auth callback route.
  - Updated `src/components/SignInForm/SignInForm.tsx` to rewrite the dev login link to use the current origin.
- Notes: Enables full login flow within the new UI.

## 2026-02-14 05:11
- Prompt: Enhance Navbar with balances and Top-Up menu; add Top-Up pages.
- Changes:
  - Created `src/api/balance.ts` to fetch user balances.
  - Created `src/pages/TopUp/Card/CardTopUp.tsx` and `src/pages/TopUp/Manual/ManualTopUp.tsx`.
  - Updated `src/components/Navbar/Navbar.tsx` to display balances and add a "Top Up" dropdown.
  - Updated `src/App.tsx` with routes for `/top-up/card` and `/top-up/manual`.
- Notes: Navbar now shows real-time balances (refreshes every 30s).

## 2026-02-14 05:15
- Prompt: Enable real Telegram login flow by configuring bot token.
- Changes:
  - Updated `secrets.dev.env` with the provided Telegram Bot Token.
  - Updated `src/components/SignInForm/SignInForm.tsx` to prioritize the "Check Telegram" message over the dev link.
  - Restarted the API service to apply the new configuration.
- Notes: Real Telegram login is now active.

## 2026-02-14 05:17
- Prompt: Make the Telegram login link point to port 5173.
- Changes:
  - Updated `REFINANCE_UI_URL` in `secrets.dev.env` to `http://localhost:5173`.
  - Restarted the API service.
- Notes: Login links sent via Telegram will now correctly redirect to the new UI.

## 2026-02-14 05:30
- Prompt: Fix balance display issue (missing authentication token).
- Changes:
  - Updated `src/api/balance.ts` to retrieve the auth token from `useAuthStore` and include it in the `apiRequest`.
- Notes: Balances should now be visible in the Navbar.

## 2026-02-14 05:31
- Prompt: Display pending (draft) balances in the Navbar.
- Changes:
  - Updated `src/components/Navbar/Navbar.tsx` to display draft balances below the completed balances in smaller, gray text.
- Notes: Draft balances are shown with a "+" sign if positive.

## 2026-02-14 05:34
- Prompt: Left-align balance text in Navbar.
- Changes:
  - Updated `src/components/Navbar/Navbar.tsx` to use `align="flex-start"` for the balance stack.
- Notes: Balance numbers and currency codes are now left-aligned.

## 2026-02-14
- Prompt: Replace Refinance text with logo.png in assets.
- Changes:
  - Updated `src/components/Navbar/Navbar.tsx` to display `logo.png` from `src/assets/` instead of the "Refinance" title.
- Notes: Add `logo.png` to `src/assets/` for the logo to appear.

## 2026-02-14
- Prompt: Implement card top-up flow (Keepz) with dialog and payment card page.
- Changes:
  - Created `src/api/deposits.ts` for createKeepzDeposit and getDeposit API calls.
  - Created `src/utils/formatRelativeTime.ts` for human-readable relative time.
  - Refactored `src/pages/TopUp/Card/CardTopUp.tsx` with Modal, amount/currency form, and mutation.
  - Created `src/pages/DepositDetail/DepositDetail.tsx` with payment card, QR code, payment link + copy, polling every 10s.
  - Added route `/deposits/:id` for deposit detail page.
  - Installed `qrcode.react` and `@tabler/icons-react`.
- Notes: Card top-up creates Keepz deposit and navigates to payment page. Auto-polling every 10 seconds.

## 2026-02-14
- Prompt: Fix Keepz deposit API - send params as query string like old UI.
- Changes:
  - Updated `src/api/deposits.ts` to send `to_entity_id`, `amount`, `currency` as URL query parameters instead of JSON body.
- Notes: FastAPI endpoint expects query params (matches old Flask UI behavior).

## 2026-02-14
- Prompt: Add Keepz dev mode to bypass auth when not configured.
- Changes:
  - Added `REFINANCE_KEEPZ_DEV_MODE` to API config; when enabled, uses mock payment URL when Keepz auth fails.
  - Updated `api/app/config.py` and `api/app/services/deposit_providers/keepz.py`.
  - Set `REFINANCE_KEEPZ_DEV_MODE=1` in `secrets.dev.env`.
- Notes: Restart API (`docker compose restart api`) for the env var to take effect.

## 2026-02-14
- Prompt: Dev success dialog with confetti, old/new balance, redirect on OK.
- Changes:
  - Added `POST /deposits/:id/complete-dev` backend endpoint for dev-mode deposits.
  - Installed `canvas-confetti`.
  - Updated `DepositDetail`: dev deposits auto-complete after 10s; on completion, show success modal with confetti, strikethrough old balance and new balance for the currency, OK button redirects to /.
- Notes: Dev-only flow for Keepz mock deposits.

## 2026-02-14 04:57
- Prompt: Implement persistent app layout with Navbar and Home page.
- Changes:
  - Created `src/components/Navbar/Navbar.tsx` with logo and logout button.
  - Created `src/components/AppLayout/AppLayout.tsx` using Mantine AppShell.
  - Created `src/pages/Home/Home.tsx` placeholder page.
  - Updated `src/App.tsx` to wrap protected routes with `AppLayout`.
- Notes: Replaced SessionStatusCard with a proper dashboard layout.

## 2026-02-14 14:30
- Prompt: Update UI theme from blue to black/white/gray only.
- Changes:
  - Added `createTheme` in `src/main.tsx` with `primaryColor: 'gray'` and `primaryShade`.
  - Replaced semantic colors in SignInForm, CardTopUp, Navbar, SessionStatusCard, DepositDetail (red/green → gray).
- Notes: Dark theme unchanged; Mantine drives primary UI colors.

## 2026-02-14 15:00
- Prompt: Solid black/white buttons with opposite-color borders on hover.
- Changes:
  - Added `variantColorResolver` in `src/main.tsx` for filled/default/light/subtle/outline variants.
  - Added hover border CSS in `src/index.css` for Button and ActionIcon.
- Notes: Resolver uses theme white/black; CSS adds 2px opposite border on hover. Fixed layout shift by using transparent 2px border by default.

## 2026-02-14 15:15
- Prompt: Copy button in deposit still sucks.
- Changes:
  - DepositDetail copy ActionIcon: variant filled → default (black bg, white icon), size lg, icon 20px.
  - Added ActionIcon default/light hover border CSS.
- Notes: Copy now contrasts as secondary action next to white Pay now.

## 2026-02-14 15:20
- Prompt: Remove borders completely.
- Changes:
  - Removed all custom border CSS for Button and ActionIcon from `src/index.css`.
- Notes: Also set outline variant border to transparent in theme resolver.

## 2026-02-14 15:25
- Prompt: Payment is bullshit with copy button not the same.
- Changes:
  - DepositDetail copy ActionIcon: variant default → filled to match Pay now (white bg, black icon).
- Notes: Both buttons now share the same visual style.

## 2026-02-14 15:30
- Prompt: Now button and copy button are different colors.
- Changes:
  - Replaced copy ActionIcon with Button in DepositDetail so both use the same component and variantColorResolver.
- Notes: Same component = identical styling. Added explicit variant="filled" to Pay now button so both use our resolver.

## 2026-02-14 15:45
- Prompt: Fix currencies centered; pending below them without shifting; position absolute bottom -80%, relative container.
- Changes:
  - Navbar: currency blocks use relative wrapper, centered text; pending uses position absolute bottom -80%, left 50%, translateX(-50%).
- Notes: Pending no longer affects layout; currencies centered. Reverted to left alignment (textAlign left, pending left 0).

## 2026-02-14 16:00
- Prompt: Profile page and navbar username link.
- Changes:
  - Navbar: username is now a Button linking to `/profile`.
  - Profile page at `/profile`: entity details (username, ID, name, tags, active, created with relative date), social links (Telegram, Signal) with open buttons, balance card, transactions table, invoices table.
  - New `DataTable` UI component for reusable tables.
  - New API modules: `entities.ts` (getMe), `transactions.ts`, `invoices.ts`.
  - Extended `types/api.ts` with Entity, Transaction, Invoice, PaginatedResponse.
  - New `utils/date.ts` with formatRelativeDate and formatDateTime.
- Notes: Profile fetches entities/me, balances, transactions, invoices via TanStack Query. Social links: t.me/{username} or tg://user?id={id} for Telegram; signal.me/#p/{phone} for Signal.

## 2026-02-14 16:15
- Prompt: Navbar user dropdown instead of separate username and logout buttons.
- Changes:
  - Navbar: Replaced username button and logout button with a single Menu dropdown (same pattern as Top Up). Username is the trigger; dropdown contains Profile link, Menu.Divider, and red Logout item.
  - Fallback: When actorEntity is null (loading), show standalone red Logout button.
- Notes: Logout uses color="red" for red-ish styling; Menu.Divider adds spacing between Profile and Logout.

## 2026-02-14 17:00
- Prompt: Profile page updates: tags, Telegram, timezone, table columns.
- Changes:
  - Tags: Moved to distinct row; new TagBadge component with colored styling (hsl formula, background tint). Table tags: same styling, +N overflow when >3.
  - Telegram ID: Copyable on click (dashed underline), icon-only ActionIcon link to t.me (or t.me/username), "Copied!" tooltip.
  - Timezone fix: formatRelativeTime and formatDateTime treat API timestamps without timezone as UTC (append Z before parsing).
  - Transaction table: merged Amount+Currency column, removed Currency; status colors (draft=gray, completed=green).
  - Invoice table: tags with TagBadge, status colors (paid=green, cancelled=red, pending=gray).
- Notes: TagBadge uses hsl((id*41.9)%360, 66%, 44%) for border/text, hsla for background. UTC fix affects DepositDetail and all date displays.

## 2026-02-14 17:30
- Prompt: Profile fixes per user feedback.
- Changes:
  - Telegram ID: dashed underline and copyable only on the ID (not "Telegram:"); removed all tooltips; fixed link to tg://user?id=XXX for numeric IDs so icon opens user profile.
  - TagBadge: simplified to add only background color derived from border color (hsla), removed extra styling (fontSize, lineHeight).
  - Table From/To entity tags: left as plain text (no changes).
- Notes: tg:// links open Telegram app for numeric IDs; https://t.me/username for usernames.

## 2026-02-14 17:45
- Prompt: Entity tags in From/To columns not styled.
- Changes:
  - Transactions table: From and To columns now render entity tags with TagBadge (colored) instead of plain text.
  - Invoices table: Same for From and To columns.
- Notes: renderTags used for entity tags next to names; +N overflow when >3 tags.

## 2026-02-14 18:00
- Prompt: +N overflow tag has white/light background that clashes with dark theme.
- Changes:
  - TagBadge overflow: removed light background; +N badge now uses transparent background with gray border/text only.
- Notes: none.

## 2026-02-14 18:05
- Prompt: Slightly increase padding for tags.
- Changes:
  - TagBadge: padding 0.1rem 0.2rem → 0.15rem 0.35rem.
- Notes: none.

## 2026-02-14 18:06
- Prompt: Slightly increase space between tags.
- Changes:
  - Profile: all tag Groups gap 4 → 6 (renderTags, From/To columns, profile card tags).
- Notes: none.

## 2026-02-14 18:10
- Prompt: Move tags, time, and currency to distinct components.
- Changes:
  - TagList: new component for tags with TagBadge and +N overflow.
  - RelativeDate: new component for relative date with tooltip (full datetime).
  - AmountCurrency / AmountsCurrency: new components for amount + currency display.
  - Profile: uses TagList, RelativeDate, AmountCurrency, AmountsCurrency.
- Notes: Reusable UI components in ui/ folder.

## 2026-02-14 18:15
- Prompt: Add tooltip on copy for Telegram ID; remove Telegram button.
- Changes:
  - Telegram ID: restored Tooltip ("Click to copy" / "Copied!") on copy; removed ActionIcon link button.
- Notes: none.

## 2026-02-14 18:20
- Prompt: Remove Signal button; make Signal ID copyable like Telegram.
- Changes:
  - Signal ID: same as Telegram - dashed underline, click to copy, tooltip ("Click to copy" / "Copied!"); removed Open button.
- Notes: none.

## 2026-02-14 18:25
- Prompt: Logout should be confirmed with dialog.
- Changes:
  - Navbar: Logout opens confirmation Modal ("Are you sure you want to logout?") with Cancel and Logout buttons.
- Notes: Uses useDisclosure for modal state; both menu and fallback logout trigger the same dialog.

## 2026-02-14 18:30
- Prompt: Top up by card dialog redirects when it shouldn't.
- Changes:
  - CardTopUp: closeOnClickOutside={false} to prevent spurious redirect when menu closes; added Cancel button.
- Notes: Click from menu closing was propagating to modal overlay and triggering onClose.

## 2026-02-14 18:35
- Prompt: Logo should be clickable and redirect to home.
- Changes:
  - Navbar: wrapped logo in Link to="/".
- Notes: none.
