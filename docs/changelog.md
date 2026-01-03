# Changelog

All notable changes to this project will be documented in this file.
---
## [0.3.1](https://github.com/JacobCoffee/debug-toolbar/compare/v0.3.0..v0.3.1) - 2026-01-03

### Bug Fixes

- handle gzip-compressed responses in toolbar injection (#24) - ([6f15ec0](https://github.com/JacobCoffee/debug-toolbar/commit/6f15ec0ee2388807cb6b469dadf7e5fed31d0534)) - Jacob Coffee

### Documentation

- regenerate changelog for v0.3.0 - ([ec85e0d](https://github.com/JacobCoffee/debug-toolbar/commit/ec85e0d3ab4c2e75dac4daee9a2d9a33fa2e5f8e)) - github-actions[bot]
- update PLAN.md for v0.3.0 release - ([0fb354b](https://github.com/JacobCoffee/debug-toolbar/commit/0fb354bf6610026933699f5d650d6c9f93dcb4c4)) - Jacob Coffee

### Features

- **(adapters)** add Starlette and FastAPI framework support (#20) - ([eec0ab2](https://github.com/JacobCoffee/debug-toolbar/commit/eec0ab2392619c04e68173103c2859050227c6c3)) - Jacob Coffee
- **(panels)** add WebSocket Panel for real-time connection tracking (#19) - ([ac1b97f](https://github.com/JacobCoffee/debug-toolbar/commit/ac1b97f91d2b02ebce182a415f61e44844f9320d)) - Jacob Coffee
- add brotli and zstd decompression support for toolbar injection (#37) - ([4d8f3f3](https://github.com/JacobCoffee/debug-toolbar/commit/4d8f3f3f30552a51decbd88ebc605bd8a2c23235)) - Jacob Coffee

### Miscellaneous Chores

- bump version to 0.3.1 - ([47a5d2e](https://github.com/JacobCoffee/debug-toolbar/commit/47a5d2ecae872499f90f61f29c3c4e8db6d2c59c)) - Jacob Coffee

### Build

- **(deps)** bump the actions group across 1 directory with 5 updates (#22) - ([e743273](https://github.com/JacobCoffee/debug-toolbar/commit/e743273bfa75c0e7c37777646ec415ffd9801a16)) - dependabot[bot]
- **(deps)** bump the actions group with 5 updates (#23) - ([51d51ce](https://github.com/JacobCoffee/debug-toolbar/commit/51d51ce10a5f49f412a198ed1ae076bcdea3a739)) - dependabot[bot]

---
## [0.3.0](https://github.com/JacobCoffee/debug-toolbar/compare/v0.2.0..v0.3.0) - 2025-11-30

### Bug Fixes

- **(mcp)** FileToolbarStorage now reloads from disk on every read - ([215f1f9](https://github.com/JacobCoffee/debug-toolbar/commit/215f1f986672f7bd700244732495782f5f0838cc)) - Jacob Coffee
- **(mcp)** convert timing from seconds to milliseconds - ([bb72f84](https://github.com/JacobCoffee/debug-toolbar/commit/bb72f84bb4a888ab4b1161bc76f750ea4ae407d8)) - Jacob Coffee
- correct example to raise `n+1` error (#13) - ([f6ae942](https://github.com/JacobCoffee/debug-toolbar/commit/f6ae942aaaad2187dac4332f0fc5df1bbbaa7975)) - Cody Fincher
- add git-cliff changelog configuration - ([7e67e7b](https://github.com/JacobCoffee/debug-toolbar/commit/7e67e7b065f965deb234614c751ef10dd111f4a3)) - Jacob Coffee
- correct MCP example panel paths and type annotations - ([80e4d16](https://github.com/JacobCoffee/debug-toolbar/commit/80e4d1615220d66ff6488e3507756551a793bc05)) - Jacob Coffee
- escape CSS braces and add dark mode support to MCP example - ([c1c2e37](https://github.com/JacobCoffee/debug-toolbar/commit/c1c2e37405e1181b1412b6af6008f6158f40fba0)) - Jacob Coffee

### Documentation

- update PLAN.md for MCP Server completion (PR #16) - ([b737f2e](https://github.com/JacobCoffee/debug-toolbar/commit/b737f2e29d9802032af422597f757a0cc286bc10)) - Jacob Coffee
- add MCP documentation and usage examples - ([34c3804](https://github.com/JacobCoffee/debug-toolbar/commit/34c3804e1c0c2f47605c512c1ce0d08b4353b9e0)) - Jacob Coffee
- add MCP integration screenshot to README and docs - ([b197d29](https://github.com/JacobCoffee/debug-toolbar/commit/b197d299fa780efb8db1e2b6b4cdf448c3634e2b)) - Jacob Coffee
- update PLAN.md with MCP completion status - ([652c755](https://github.com/JacobCoffee/debug-toolbar/commit/652c755e600e779f49348863ddd7eb55ac600ff4)) - Jacob Coffee
- update MCP screenshot and API docs for FileToolbarStorage (#18) - ([38e9a4b](https://github.com/JacobCoffee/debug-toolbar/commit/38e9a4b756f87dc2fcea03d5b6c8b5dcabc3fb3b)) - Jacob Coffee
- regenerate changelog for v0.3.0 - ([8e6f21c](https://github.com/JacobCoffee/debug-toolbar/commit/8e6f21cbc5fb6f3a4f4237a453e43057c3eaf881)) - github-actions[bot]

### Features

- **(mcp)** add FileToolbarStorage for shared persistence between web app and MCP server - ([6afbff5](https://github.com/JacobCoffee/debug-toolbar/commit/6afbff5faeef7c1bce3306e385dca0ed3043a3ed)) - Jacob Coffee
- add AsyncProfilerPanel for async task tracking (#14) - ([dd92b33](https://github.com/JacobCoffee/debug-toolbar/commit/dd92b330ea50480d5afb8ee974f01b76b79487a7)) - Jacob Coffee
- add GraphQL Panel with Strawberry integration (#15) - ([af70e9c](https://github.com/JacobCoffee/debug-toolbar/commit/af70e9c44529ccdbc0347008c80265800c2f6393)) - Jacob Coffee
- add MCP server for AI assistant integration (#16) - ([fa880ba](https://github.com/JacobCoffee/debug-toolbar/commit/fa880ba5fda9fe303aa70f9951ee45c134e67b5f)) - Jacob Coffee
- add interactive HTML frontend to MCP example - ([48d5bf1](https://github.com/JacobCoffee/debug-toolbar/commit/48d5bf1137660c5d545934434425297928127dca)) - Jacob Coffee

### Release

- v0.3.0 with MCP Server integration (#17) - ([5621580](https://github.com/JacobCoffee/debug-toolbar/commit/5621580a22f12342cb7f3c46ad013e2ee3866c46)) - Jacob Coffee

---
## [0.2.0](https://github.com/JacobCoffee/debug-toolbar/compare/v0.1.4..v0.2.0) - 2025-11-29

### Bug Fixes

- **(ci)** disable debug-toolbar publish, fix litestar wheel build - ([88427d3](https://github.com/JacobCoffee/debug-toolbar/commit/88427d38c5eba97a52cb19339fda394ce027dd9a)) - Jacob Coffee
- **(docs)** correct GitHub URL to debug-toolbar - ([3e395fd](https://github.com/JacobCoffee/debug-toolbar/commit/3e395fdacc18ec9d2510d35014e3d8d66cce545c)) - Jacob Coffee
- **(examples)** add light theme support to N+1 demo page - ([250b2fa](https://github.com/JacobCoffee/debug-toolbar/commit/250b2fa72ac7bc4f68f71bad9739b2c4eb66b95e)) - Jacob Coffee
- **(examples)** restore dark mode as default in N+1 demo - ([b644b66](https://github.com/JacobCoffee/debug-toolbar/commit/b644b665680a363840babdbef7ca3e8b40633a95)) - Jacob Coffee
- **(examples)** restore dark mode as default in N+1 demo - ([445e53e](https://github.com/JacobCoffee/debug-toolbar/commit/445e53e2e6d4dd0ad83be33562e17a37146b5ac0)) - Jacob Coffee
- **(examples)** add text color to N+1 demo link on home page - ([c65421b](https://github.com/JacobCoffee/debug-toolbar/commit/c65421b7c8c4b6658f5b6cfd39be0d3d959074b8)) - Jacob Coffee
- **(tests)** make lifecycle hook test more robust - ([5e6f3e4](https://github.com/JacobCoffee/debug-toolbar/commit/5e6f3e42a1320b5085bfee0390ddc7e61f5f9a32)) - Jacob Coffee
- **(tests)** remove flaky after_request assertion in CI - ([cfe8a3d](https://github.com/JacobCoffee/debug-toolbar/commit/cfe8a3da844ecbfa09dc6b75f3d433cc0ce42f77)) - Jacob Coffee

### Documentation

- add comparison page to documentation - ([605e8fe](https://github.com/JacobCoffee/debug-toolbar/commit/605e8fe25b63e3306fbee6cabbcd5e25ac32dbcd)) - Jacob Coffee
- restructure documentation layout (#6) - ([cef8237](https://github.com/JacobCoffee/debug-toolbar/commit/cef823706ac9ba999ab91ced2b5f9f504e792267)) - Jacob Coffee
- improve index page with installation tabs and card grid (#7) - ([eccdc97](https://github.com/JacobCoffee/debug-toolbar/commit/eccdc9777f33a28ad2ce59884318b78122fa3773)) - Jacob Coffee
- comprehensive documentation overhaul for 110% quality - ([1e07998](https://github.com/JacobCoffee/debug-toolbar/commit/1e07998311fb1af4370c312d6306b016ce4cd38a)) - Jacob Coffee
- add panel screenshots to README and documentation - ([e11af10](https://github.com/JacobCoffee/debug-toolbar/commit/e11af1095572e40b68f146374fd000a4f6dc4843)) - Jacob Coffee
- add panel screenshots to index page grid - ([42f3118](https://github.com/JacobCoffee/debug-toolbar/commit/42f31189f774ab55566ecd8e2babdaec95603093)) - Jacob Coffee
- update version to 0.2.0 and add profiler config options - ([1453304](https://github.com/JacobCoffee/debug-toolbar/commit/1453304d4d60046c0b2441afc5b1abeac7649787)) - Jacob Coffee

### Features

- **(alerts)** add proactive issue detection panel (#10) - ([5de5b03](https://github.com/JacobCoffee/debug-toolbar/commit/5de5b03c276f029b7d18f0334db2039b861bc0d0)) - Jacob Coffee
- **(ci)** add documentation preview and GitHub Pages workflows (#3) - ([8939398](https://github.com/JacobCoffee/debug-toolbar/commit/893939848e559147fdd15eef72ac557bac0c35e0)) - Jacob Coffee
- **(events)** add Events Panel for Litestar lifecycle tracking (#9) - ([4cb8136](https://github.com/JacobCoffee/debug-toolbar/commit/4cb8136c3b40a7aa1efbcc4501dff7dbdacdc72a)) - Jacob Coffee
- **(memory)** add multi-backend memory profiling panel (#12) - ([35a3f0d](https://github.com/JacobCoffee/debug-toolbar/commit/35a3f0d14d1e9222a182fe14170bbd7c9931c229)) - Jacob Coffee
- **(profiling)** add flame graph visualization support (#11) - ([632fc93](https://github.com/JacobCoffee/debug-toolbar/commit/632fc933017b0ab15a1cad70bc8278b6b9f54aa7)) - Jacob Coffee
- **(profiling)** filter stdlib and prioritize user code - ([7cd29f9](https://github.com/JacobCoffee/debug-toolbar/commit/7cd29f9d6a6aa7b0b4dca6404493bbafed214727)) - Jacob Coffee
- **(sql)** add EXPLAIN query plans for SQLAlchemy panel (#5) - ([7abf410](https://github.com/JacobCoffee/debug-toolbar/commit/7abf410f755e37882fcb686045eb70a189b88973)) - Jacob Coffee
- **(sql)** add N+1 query detection to SQLAlchemy panel (#8) - ([bb5cfca](https://github.com/JacobCoffee/debug-toolbar/commit/bb5cfca446014e90466d9463733e15298c121cc1)) - Jacob Coffee
- **(ui)** Phase 5 - Complete toolbar UI with themes, positioning, and history (#4) - ([2d5c8c0](https://github.com/JacobCoffee/debug-toolbar/commit/2d5c8c0279ce4a55dafce0d0e90bcc0e3bbc1008)) - Jacob Coffee
- **(ui)** add screenshots and fix full-width top/bottom toolbar - ([7422535](https://github.com/JacobCoffee/debug-toolbar/commit/7422535d4a7bbed8d43721ffa403226f54e0e083)) - Jacob Coffee
- **(ui)** add styled panel rendering for inline toolbar - ([6e554e8](https://github.com/JacobCoffee/debug-toolbar/commit/6e554e8d20cb8fefccdaa371aba456f5ee8cbd7f)) - Jacob Coffee
- Phase 10 - Additional Panels (#2) - ([a791283](https://github.com/JacobCoffee/debug-toolbar/commit/a79128374f83db81d12ed0c477fd4d139aae6e44)) - Jacob Coffee

### Miscellaneous Chores

- bump version to 0.2.0 - ([2e222f6](https://github.com/JacobCoffee/debug-toolbar/commit/2e222f6fa24bb2be79a27a2cc2dcf6fe8ea14660)) - Jacob Coffee

### Refactoring

- **(middleware)** extract ResponseState and improve error handling - ([6b54458](https://github.com/JacobCoffee/debug-toolbar/commit/6b54458bc7a01cf96daf5ca4dd1c7af367ecda2e)) - Jacob Coffee

---
## [0.1.4](https://github.com/JacobCoffee/debug-toolbar/compare/v0.1.3..v0.1.4) - 2025-11-27

### Bug Fixes

- **(ci)** repack wheel/sdist for litestar-debug-toolbar name - ([3ad5d68](https://github.com/JacobCoffee/debug-toolbar/commit/3ad5d68b6d1383d4d58a45037672e5caefa59095)) - Jacob Coffee

---
## [0.1.3](https://github.com/JacobCoffee/debug-toolbar/compare/v0.1.2..v0.1.3) - 2025-11-27

### Features

- **(ci)** publish to both debug-toolbar and litestar-debug-toolbar - ([93e29fc](https://github.com/JacobCoffee/debug-toolbar/commit/93e29fc58a43bc8a76d656142d621eb1fc0f61ea)) - Jacob Coffee

---
## [0.1.2](https://github.com/JacobCoffee/debug-toolbar/compare/v0.1.1..v0.1.2) - 2025-11-27

### Bug Fixes

- **(ci)** update sigstore action to v3.1.0 - ([c37b1d5](https://github.com/JacobCoffee/debug-toolbar/commit/c37b1d53083e684ea024038475d809dc362d50d4)) - Jacob Coffee

---
## [0.1.1](https://github.com/JacobCoffee/debug-toolbar/compare/v0.1.0..v0.1.1) - 2025-11-27

### Build

- **(deps)** bump the actions group with 6 updates (#1) - ([860811f](https://github.com/JacobCoffee/debug-toolbar/commit/860811fe5031a7a04131529219dd98faabf76a4d)) - dependabot[bot]

---
## [0.1.0] - 2025-11-27

### Bug Fixes

- update act-ci Makefile target for CI workflow jobs - ([0c550d2](https://github.com/JacobCoffee/debug-toolbar/commit/0c550d239111b894f7b084b8cfb90a4bb31912cf)) - Jacob Coffee
- update test-cov target for unified debug_toolbar package - ([6daa6c5](https://github.com/JacobCoffee/debug-toolbar/commit/6daa6c507e551f0a03d5f31cbfdcc4b4940430e1)) - Jacob Coffee

### Documentation

- add Sphinx documentation with API reference - ([82df082](https://github.com/JacobCoffee/debug-toolbar/commit/82df08217771a3a504caedf04b735e2b9a00ab0d)) - Jacob Coffee
- update README with new package structure and badges - ([637bf0d](https://github.com/JacobCoffee/debug-toolbar/commit/637bf0dddc721edc4d1b182a4a4484ee74795bcd)) - Jacob Coffee
- add CONTRIBUTING.rst with development guidelines - ([134f1e5](https://github.com/JacobCoffee/debug-toolbar/commit/134f1e5fc50d1afc26cd1105a20aeecf4c980ae5)) - Jacob Coffee

### Features

- add framework-agnostic core debug toolbar package - ([21d31a2](https://github.com/JacobCoffee/debug-toolbar/commit/21d31a25560bf31ffbae9464bd50159012697221)) - Jacob Coffee
- add Litestar framework integration - ([c1abc92](https://github.com/JacobCoffee/debug-toolbar/commit/c1abc927fbee98335bc2af84cabdbacc9eb4e28e)) - Jacob Coffee
- add Advanced-Alchemy SQLAlchemy panel - ([1801c5f](https://github.com/JacobCoffee/debug-toolbar/commit/1801c5f782be4f349632db308f4bada8e718c920)) - Jacob Coffee

### Refactoring

- rename old module references to debug-toolbar - ([9cb8dfe](https://github.com/JacobCoffee/debug-toolbar/commit/9cb8dfe709172444443957a7bec52ae7f05d7cf4)) - Jacob Coffee

### Tests

- add unit and integration tests - ([0604eaa](https://github.com/JacobCoffee/debug-toolbar/commit/0604eaa09e66a2066dc78c8cb765e1e9772c1caf)) - Jacob Coffee
- increase coverage to 96% with comprehensive tests - ([f29de78](https://github.com/JacobCoffee/debug-toolbar/commit/f29de78fb66ba21ef36e2e4b943fda0416295c13)) - Jacob Coffee

### Build

- add project configuration with uv_build backend - ([75073ed](https://github.com/JacobCoffee/debug-toolbar/commit/75073ed7aa933ce837871c19968c622b58ec4079)) - Jacob Coffee

### Ci

- add dependabot configuration - ([63aeed4](https://github.com/JacobCoffee/debug-toolbar/commit/63aeed42b92ce27cda58d773ae0fbfc2e8fe03bb)) - Jacob Coffee
- add changelog workflow - ([10af18d](https://github.com/JacobCoffee/debug-toolbar/commit/10af18da186137aaaf11db3c7079df844cb8a36e)) - Jacob Coffee
- add PR title linting workflow - ([bef3add](https://github.com/JacobCoffee/debug-toolbar/commit/bef3addf1d7eb7ecc722fdbe1485b0d5d83a7ff5)) - Jacob Coffee
- add release notes configuration - ([9a0e775](https://github.com/JacobCoffee/debug-toolbar/commit/9a0e77578a174dbe50cc067c62ff3d5900c03e2f)) - Jacob Coffee
- add issue templates - ([9177bcc](https://github.com/JacobCoffee/debug-toolbar/commit/9177bccdf981215044af9bbde2c8fc5d5e341406)) - Jacob Coffee
- add CI workflow - ([6869512](https://github.com/JacobCoffee/debug-toolbar/commit/6869512f27bc4ac2ed87257cb41dc3b2b4f4c9a2)) - Jacob Coffee
- add publish workflow - ([70721ec](https://github.com/JacobCoffee/debug-toolbar/commit/70721ec433e28c3681e4ac9bcb20275e48a7eb20)) - Jacob Coffee
- add PR template - ([9f56a4c](https://github.com/JacobCoffee/debug-toolbar/commit/9f56a4cc649ae66dba9184389c43943bd37a1211)) - Jacob Coffee

### Examples

- add usage examples for ASGI and Litestar - ([15a9854](https://github.com/JacobCoffee/debug-toolbar/commit/15a985420659bf7f258268ac7555a16bc2825713)) - Jacob Coffee

``debug-toolbar`` Changelog
