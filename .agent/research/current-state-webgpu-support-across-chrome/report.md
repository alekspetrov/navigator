# WebGPU Support Across Chrome, Firefox and Safari: State of Play and Remaining Gaps

## Summary

All three major browser engines now ship WebGPU by default in at least one stable
configuration: Chromium since Chrome 113 (2023), Firefox since 141 (July 2025), and Safari
since 26.0 (September 2025) — a milestone announced as "WebGPU is now supported in major
browsers" in November 2025 [1][2]. That headline hides the real shape of the field:
"shipped" means a different platform matrix in each engine, and the W3C GPU for the Web
implementation-status wiki — the closest thing to a canonical tracker — records per-OS,
per-GPU-vendor, per-driver rows rather than a single yes/no [2]. Chromium is default-on
across Mac, Windows x86/x64, ChromeOS and much of Android, but Linux is enabled only for
specific vendor/driver combinations and Windows on ARM64 is still behind a flag [2].
Firefox is default-on for Windows and (from 145/147) Apple Silicon macOS, with Linux, Intel
Macs and Android still flagged or Nightly-only, and Mozilla's own shipping post enumerates
concrete gaps such as missing `importExternalTexture` [2][3]. Safari's support is gated on
operating-system version rather than browser version: WebGPU is on by default in macOS Tahoe
26, iOS 26, iPadOS 26 and visionOS 26 and effectively unavailable below that [4]. The
strongest counter-position to the "it's done" framing comes from the support tables
themselves — caniuse still classifies Firefox as "disabled by default" through version 158
and Safari desktop as only "partial support" through 26.6 and 27/TP [5]. Above the platform
layer there is a second, less-discussed divergence: optional features and language
extensions. Compatibility mode, subgroup controls, immediates and several WGSL extensions
have shipped in Chrome, and this corpus records no announced shipping date for them in
Firefox or Safari [6][7].
What the corpus cannot settle is the current *feature-level* conformance of Firefox and
Safari — no source here enumerates their supported `GPUFeatureName` sets or CTS pass rates.

## Snapshot: what "supported" means per engine

| Engine | Default-on platforms | Flagged / in-progress | Backend |
|---|---|---|---|
| Chromium (Chrome, Edge) | Mac, Windows x86/x64, ChromeOS (113); Android 12+ on ARM/Qualcomm/Intel (121), Imagination on Android 16+ (139); Linux on Intel Gen12+ (144) and NVIDIA 535.183.01+ Wayland (147) | Samsung Xclipse "probably 154"; other Linux configs and Windows ARM64 behind `--enable-unsafe-webgpu` | Dawn (C++) [2] |
| Firefox | Windows (141); macOS Apple Silicon on macOS 26+ (145), all macOS versions (147) | Linux and Intel Macs: Nightly default-on, stable TBD; Android: `gfx.webgpu.ignore-blocklist` in Beta/Nightly | wgpu (Rust) [2] |
| Safari | macOS 26, iOS 26, iPadOS 26, visionOS 26 — all default-on | (no flagged tier documented in the tracker) | WebKit/Metal [2] |

The tracker's own framing of Safari is unusually flat compared to the other two: "In macOS
Tahoe 26, iOS 26, iPadOS 26, and visionOS 26, WebGPU is supported and enabled by default."
[2] Caniuse, which aggregates differently, scores the same three engines as fully supported
(Chrome 113–155, Edge 113+), partially supported (Safari 26.0–27/TP on desktop but *fully*
supported on iOS 26+), and disabled-by-default (Firefox 141–158, and Firefox for Android
155) [5]. The Firefox row in particular is a coarse-grained artifact — caniuse appears to
grade on the union of platforms, so a Windows-and-macOS-only default-on ship reads as
"disabled by default" — an inference from the shape of the table, not a methodology caniuse
states [5].

## Chrome and Chromium: broadest reach, platform tail still open

Chrome shipped WebGPU first, in version 113, on "ChromeOS devices with Vulkan support,
Windows devices with Direct3D 12 support, and macOS", with Android arriving in Chrome 121
for Android 12+ devices powered by Qualcomm and ARM GPUs [8] (the gpuweb tracker lists the
same Chrome 121 Android tier as ARM/Qualcomm/Intel, so the two vendor lists disagree on
Intel [2]). Linux is the long tail: as of
the tracker it is default-on only for Intel Gen12+ (Chrome 144) and NVIDIA with driver
535.183.01 or newer under Wayland (Chrome 147); everything else requires launching the
browser with `--enable-unsafe-webgpu --ozone-platform=x11 --use-angle=vulkan
--enable-features=Vulkan,VulkanFromANGLE` [2]. Windows on ARM64 is likewise flag-gated [2].
Android coverage expands vendor by vendor rather than all at once — Imagination GPUs on
Android 16+ landed in 139, Samsung Xclipse is projected for around 154, and other vendors
are listed as TBD [2].

Notable limitations documented by Chrome itself, independent of platform availability:

- **Secure-context only.** `navigator.gpu` is undefined over `http:` or `file:`; the API is
  available only in secure contexts [9]. This is a spec-level rule rather than a Chrome
  quirk — MDN states the whole API is available only in a secure context, so Firefox and
  Safari behave the same way [21].
- **Blocklisting and settings can silently remove the adapter.** `requestAdapter()` returns
  `null` when hardware acceleration is off in `chrome://settings/system`, when the GPU is on
  the blocklist ("WebGPU has been disabled via blocklist or the command line" in
  `chrome://gpu`), when no GPU is detected, or after repeated GPU-process crashes [9].
- **Software fallback is possible and slow.** `chrome://gpu` may report "WebGPU: Software
  only, hardware acceleration unavailable" rather than "Hardware accelerated" [9].
- **Windows: no simultaneous multi-adapter use** (chromium issue 329211593), and
  `powerPreference` on `requestAdapter()` has no effect — Chrome reuses the adapter already
  allocated for other Chrome workloads, which on laptops is generally the integrated GPU.
  The documented workaround is the `chrome://flags/#force-high-performance-gpu` flag [9].

Chrome is also where nearly all post-1.0 feature work lands first. Recent releases added
transient attachments and the WGSL `texture_and_sampler_let` extension (146); immediates —
push/root constants, gated on the `immediate_address_space` WGSL language feature — plus
stricter transient-attachment validation (149–150); and subgroup size control (151–152)
[6][10]. Earlier releases added the `core-features-and-limits` feature and a
compatibility-mode origin trial (139), WGSL `subgroup_id` and `uniform_buffer_standard_layout`
(144), `subgroup_uniformity` (145) and `linear_indexing` (147–148) [6]. Dawn limit tiers were
raised (`maxStorageBuffersPerShaderStage` to 16, `maxSampledTexturesPerShaderStage` to 48)
and SPIR-V validation was enabled by default on Android as a security layer against
malformed input [6]. Compatibility mode itself shipped in Chrome 146 via a Blink
intent-to-ship filed in January 2026 [7][11].

## Firefox: shipped on Windows first, platform and feature work continuing

Mozilla shipped WebGPU on Windows in Firefox 141, explaining the sequencing directly:
"Although Firefox 141 enables WebGPU only on Windows, we plan to ship WebGPU on Mac and
Linux in the coming months, and finally on Android. Windows was our first priority because
that's where the great majority of our users are" [3]. Coverage since then, per the tracker:
macOS Apple Silicon on macOS 26+ from Firefox 145, all macOS versions (Apple Silicon) from
147; Linux and non-Apple-Silicon Macs default-on in Nightly only, with Mozilla expecting to
ship Linux in 2026; Android disabled by default and reachable in Beta/Nightly by setting
`gfx.webgpu.ignore-blocklist` in `about:config`, with Android work also slated for 2026 [2].
A July 2026 issue filed against the tracker argues the Linux row is already stale — that the
Firefox 152 release channel supports WebGPU on Linux behind the `dom.webgpu.enabled`
`about:config` flag, which is a weaker claim than "shipped" but stronger than "Nightly only";
the issue was still open in the fetched revision [12].

The implementation is built on wgpu, a Rust crate that abstracts Direct3D 12, Metal and
Vulkan (and OpenGL), developed as an independent open-source project with Mozilla as a major
contributor [3][13][14]. Because wgpu already targets all those backends, launch coverage
framed the remaining macOS/Linux/Android work as robustness and automated test coverage
rather than new backend development [14].

Mozilla's own list of known gaps at the 141 ship is the most concrete limitations inventory
in the corpus for any engine [3]:

- Unbuffered IPC between web content and the GPU sandbox process added significant overhead;
  addressed in Bug 1968122, with the fix appearing in Firefox 142.
- An interval timer is used to detect GPU task completion, adding latency for short tasks;
  Bug 1870699 tracks replacing it.
- `importExternalTexture` — the path that lets the GPU read decompressed video directly from
  the decoder — is not implemented; Bug 1827116 tracks it.

Mozilla also stated plainly that "there is plenty of work remaining to be done to improve
our performance and compliance with the specification" [3]. Context on why the timeline was
long: a Firefox WebGPU team member wrote in 2024 that the team was "90% of the way there in
terms of functionality", with remaining work dominated by recent spec changes, and that the
team had three full-time engineers against "an order of magnitude more humans" on Chrome's
WebGPU [15]. A 2026 third-party guide recommends Firefox 147 or later on Windows as the
conservative production target and notes that wgpu can produce different validation messages
than Chromium's Dawn [16].

## Safari: shipped everywhere Apple ships OS 26, gated by OS version

WebKit added WebGPU in Safari 26 beta, announced at WWDC25 in June 2025, and shipped it in
Safari 26.0 on 15 September 2025 for macOS, iOS, iPadOS and visionOS [17][4]. WebKit's
positioning is unusually strong: WebGPU "supersedes WebGL on macOS, iOS, iPadOS, and
visionOS and is preferred for new sites and web apps", because it maps better to Metal than
WebGL's OpenGL-derived model does [4]. The feature had been enabled in Safari Technology
Preview for over a year before shipping, and WebKit notes that validation was recently
streamlined "to minimize overhead and maintain closer to native application performance"
[4]. WGSL is described as the safety mechanism — a language "verifiably safe for the web"
compared with shading languages that permit unchecked bounds accesses and pointer arithmetic
[4].

The dominant Safari limitation is structural rather than a missing feature: availability is
tied to the OS release, so a user on macOS 15 has no shipped WebGPU regardless of Safari
version, and on iOS every browser uses WebKit, making an OS upgrade the only path [2][16].
Beyond the OS gate, the corpus names two Apple-platform capability limits, both from
secondary sources: because WebKit maps WebGPU onto Metal, iPhone and iPad expose stricter GPU
limits (memory, maximum workgroup counts) than Macs, so pipelines and shader modules must be
sized for the lower tier [16]; and a July 2025 analysis reports Safari's Metal backend
applying default buffer-size ceilings on iOS hardware — cited as 256 MB on older iPhones
rising to roughly 993 MB on iPad Pro — which caps how large a single binding, such as a model
weight buffer, can be [22]. Neither figure is corroborated by Apple documentation in this
corpus.
The pre-26 "Experimental WebGPU" flag is not a substitute — a WebKit bug filed in September
2025 reports that on macOS 15 with Safari 26, previously working content regressed:
`InvalidStateError: GPUCommandEncoder.finish: Unable to finish.` in one viewer app and a
device loss in the WebGPU samples' rotating-cube demo, while the hello-triangle sample still
worked and the same Safari 26 on macOS 26 worked in all cases; the reporter also flagged
that there is "no easy way to detect" the difference [18]. The bug was resolved as a
duplicate [18].

Content-level interop bugs are also being reported against shipped Safari. A November 2025
Dear ImGui issue describes an Emscripten/WASM app whose simple triangle render pass works in
Safari 26.1 on macOS and iOS 26, but which loses the device as soon as the ImGui render pass
sets its pipeline — while the identical build works in Chrome and Firefox on macOS and Linux
and natively via wgpu-native [19]. The reporter could obtain no validation messages from any
browser, which points at diagnostics as well as correctness [19]. This is a single
third-party report, not a WebKit-confirmed defect, and the corpus contains no follow-up —
though the reporter states he also filed it with Apple directly, and his macOS repro ran
Safari 26.1 with WebGPU flags enabled, the same flagged pre-26 configuration implicated
above, while the iOS 26 repro used the default-on build [19].

## Cross-engine feature divergence

Beyond platform matrices, the three engines differ on optional features, WGSL extensions and
capability tiers. What this corpus establishes:

| Feature | Chrome | Firefox | Safari |
|---|---|---|---|
| Compatibility mode (`featureLevel: "compatibility"`) | Shipped in Chrome 146, Android first; ChromeOS GLES 3.1 and Windows D3D11 under exploration [6]; restricted subset [7] | Spec changes approved, "has not committed to implementing it yet" [11] | "not anticipated that this feature will ship in Safari" — all shipping Apple devices support core WebGPU [11] |
| Subgroups | `subgroup_id` (144), `subgroup_uniformity` (145) [6]; subgroup size control (151-152) [6][10] | not documented in this corpus | not documented in this corpus |
| `shader-f16` | On Vulkan requires `VK_KHR_shader_float16_int8` + 16-bit storage access; excluded on all Qualcomm Android devices [20] | Same Vulkan requirements as Chrome, so the same Qualcomm exclusion [20] | not documented in this corpus |
| `importExternalTexture` | `externalTexture` binding behaviour documented as shipped [6] | Not implemented as of the 141 ship; Bug 1827116 [3] | not documented in this corpus |
| Texture component swizzle | Added in Chrome 143, alongside removal of `bgra8unorm` read-only storage usage [6] | not documented in this corpus | not documented in this corpus |

"Not documented in this corpus" marks silence in the fetched sources, not a confirmed
absence.

**Compatibility mode — Chrome-only in practice, cross-vendor on paper.** Compatibility mode
is an opt-in, lightly restricted subset of WebGPU that can run on older graphics APIs such
as OpenGL ES 3.1 and Direct3D 11, requested via `requestAdapter({ featureLevel:
"compatibility" })` [6][7][11]. The intent quantifies the reach argument: 31% of Chrome users
on Windows do not have Direct3D feature level 11.1 or higher, 23% of Android users do not
have Vulkan 1.1 (15% have no Vulkan at all), and ChromeOS Vulkan penetration is low while
OpenGL ES 3.1 is ubiquitous [11]. It shipped in Chrome 146 (February 2026), starting with
Android, with ChromeOS on GLES 3.1 and Windows on D3D11 under exploration [6]. The Blink
intent records both Gecko and WebKit standards positions as "Positive", noting the proposal
was discussed and approved in GPU for the Web Working Group meetings with commits signed off
by working-group members from Google, Apple and Mozilla [11] — and the same intent's availability expectation answers
the question directly: Mozilla "is interested in this feature (and has approved all of the
spec changes) but has not committed to implementing it yet", while for Apple "it is not
anticipated that this feature will ship in Safari since all Apple devices on the market can
support the full Core WebGPU spec"; on the same thread Chrome's WebGPU lead added "we don't
expect all browsers to ship it ever", describing Firefox as considering it against competing
WebGPU priorities [11]. Its
restrictions are the practical cost of the wider reach [7]:

- Possibly **zero storage buffers in vertex shaders** — roughly 45% of the targeted older
  devices lack the capability; this is the restriction most likely to break existing apps.
- **One texture-binding view dimension per texture**, fixed at creation via
  `textureBindingViewDimension`; binding a cube texture as a `2d-array` view is a validation
  error.
- **No selecting a subset of layers** in `createView()` for a bind group, which complicates
  mipmap generation.
- **Color blending must match across all color targets**, and `copyTextureToBuffer` /
  `copyTextureToTexture` do not work with compressed textures, nor `copyTextureToTexture`
  with multisampled textures.

Notably, any app that stays inside the compatibility limits is still a valid core WebGPU app
and runs anywhere WebGPU already runs [7]; Chrome returns a core-capable adapter on capable
devices but the app is expected to stay within compatibility limits unless it enables
`core-features-and-limits` [6].

**shader-f16 — a spec-level exclusion, not a browser bug.** A gpuweb issue documents that to
expose `shader-f16` on Vulkan, both Chrome and Firefox require `VK_KHR_shader_float16_int8`
with `shaderFloat16`, plus `VK_KHR_16bit_storage` (or Vulkan 1.1) with
`storageBuffer16BitAccess` and `uniformAndStorageBuffer16BitAccess`. Android device surveys
cited in the issue put those at 76.5%, 64% and 42% respectively — and the set of devices
supporting the last one contains zero Qualcomm devices, so no Qualcomm Android device can
use 16-bit floats in WebGPU [20]. The issue is closed and labelled as resolved pending a
WGSL specification change [20]. This is the clearest documented case where a feature's
absence is shared by two engines and traceable to the spec's requirements rather than to
either implementation.

**Subgroups, immediates and WGSL extensions.** Subgroup-related WGSL extensions
(`subgroup_id`, `subgroup_uniformity`) and subgroup size control landed in Chrome 144, 145
and 151–152 respectively; immediates (push constants) landed in Chrome 149–150 behind the
`immediate_address_space` WGSL language feature; `linear_indexing` and
`texture_and_sampler_let` landed in 147–148 and 146 [6][10]. The corpus documents no
corresponding ship dates for Firefox or Safari, so these should be treated as feature-detected
capabilities (`navigator.gpu.wgslLanguageFeatures`, `adapter.features`) rather than assumed
baseline [10].

**Texture formats and per-adapter capability tiers.** Chrome 142 extended texture format
support capabilities, and 143 added texture component swizzle while removing `bgra8unorm`
read-only storage texture usage; Dawn raised limit tiers for storage buffers and sampled
textures per shader stage [6]. Because these surface as adapter limits rather than booleans,
the practical cross-browser rule is to read limits at runtime rather than target a fixed
profile.

**Video import.** `importExternalTexture` is explicitly unimplemented in Firefox as of the
141 ship post [3], while Chrome documents shipped changes to `externalTexture` binding
behaviour [6] — one of the few concretely asymmetric API surfaces named in the corpus.

MDN, for its part, still marks the WebGPU API as "Limited availability" and explicitly not
Baseline, "because it does not work in some of the most widely-used browsers" [21].

## Reading the evidence: where sources disagree

Three of the sources here are secondary commentary and should be weighted accordingly. A
July 2025 analysis argues that implementation bugs across all three browsers block
browser-based LLM inference, citing Chrome's multi-adapter and power-preference limits
(consistent with Chrome's own docs [9]), Safari Metal buffer-size ceilings, Chrome's
practical `maxStorageBufferBindingSize` limits, and Firefox's then-Nightly-only status [22].
Its Firefox and Safari status claims predate the Firefox 141 and Safari 26.0 ships and are
now out of date, and its numeric claims (for example, that only 65% of users have
WebGPU-capable browsers) are uncited in the fetched text [22]. A 2026 vendor guide gives
per-engine production targeting advice — Firefox 147+ on Windows, macOS/iOS/iPadOS/visionOS
26+ for WebKit, and stricter mobile GPU limits on Apple platforms — but is marketing content
with no primary citations [16]. Two further items are launch-day press coverage of the
Firefox 141 announcement; the linuxiac piece adds no primary facts beyond the Mozilla post
[14], while the itsfoss piece adds one hands-on data point — a rotating-cube demo rendered
cleanly, but a Unity WebGPU game (Project Prismatic) ran at barely 30 FPS, dipping to 10-18,
with occasional freezes, on the Firefox 141 beta with `dom.webgpu.enabled` and
`dom.webgpu.allow-present-without-readback` set [13]; one of
them misstates the Safari version as "Safari 16" [14]. Where any of these conflict with the
gpuweb tracker [2], vendor release notes [3][4][6] or caniuse [5], prefer the latter.

## Key findings

- (pattern) All three engines ship WebGPU by default in at least one stable configuration as
  of late 2025, making cross-engine WebGPU a real target rather than a Chromium-only one
  [1][2].
- (pitfall) "Supported" is per-OS and per-GPU-vendor, not per-browser: Chromium's Linux
  support is limited to Intel Gen12+ and NVIDIA 535.183.01+ under Wayland, with everything
  else behind `--enable-unsafe-webgpu` [2].
- (pitfall) Safari's WebGPU availability is gated on OS version (macOS/iOS/iPadOS/visionOS
  26), and the pre-26 experimental flag regressed with Safari 26 on macOS 15 with no easy
  runtime way to distinguish the two configurations [4][18].
- (pitfall) Firefox does not implement `importExternalTexture`, so zero-copy
  video-to-GPU paths need a fallback there [3].
- (decision) Chrome ships compatibility mode (146) as an opt-in restricted subset requested
  via `featureLevel: "compatibility"`, trading features for reach on OpenGL ES 3.1 and D3D11
  class hardware [6][7].
- (pitfall) The heaviest compatibility-mode restriction is that roughly 45% of target devices
  expose zero storage buffers in vertex shaders, which breaks a common WebGPU idiom [7].
- (learning) `shader-f16` is unavailable on all Qualcomm Android devices because the Vulkan
  requirements both Chrome and Firefox enforce include `uniformAndStorageBuffer16BitAccess`,
  present on only ~42% of surveyed Android devices and no Qualcomm parts [20].
- (pattern) Post-1.0 feature velocity is concentrated in Chrome — immediates, subgroup size
  control, transient attachments and several WGSL extensions shipped there with no documented
  ship dates elsewhere — so feature-detect via `wgslLanguageFeatures` and `adapter.features`
  rather than assuming a baseline [6][10].
- (pitfall) On Windows, Chrome ignores `powerPreference` and cannot use multiple adapters
  simultaneously, so discrete-GPU selection is not controllable from the page [9].
- (decision) Mozilla shipped Windows first deliberately (user share), leaving macOS, Linux
  and Android to follow as robustness and test coverage caught up [3].
- (learning) Support tables disagree by construction: caniuse grades Firefox as "disabled by
  default" through 158 and Safari desktop as "partial", while the gpuweb tracker shows both
  as shipped on specific platforms — reconcile against the tracker plus vendor release notes
  [2][5].
- (pitfall) Shipped-and-default-on does not imply content-level interop: a WASM/Emscripten
  Dear ImGui app loses the device on Safari 26.1 while working in Chrome and Firefox, with no
  validation messages from any engine [19].

## Open questions

- **What optional features does each engine actually expose?** No source here enumerates
  `GPUFeatureName` support (for example `timestamp-query`, `depth32float-stencil8`,
  `texture-compression-*`, subgroups) per browser. A maintained WebGPU feature matrix, or
  per-implementation CTS dashboards, would settle it.
- **Conformance-test standing.** Mozilla stated in July 2025 that spec-compliance work
  remained [3], and a Firefox engineer estimated ~90% functional completeness in 2024 [15];
  no source gives current CTS pass rates for wgpu, Dawn or WebKit.
- **Firefox on Linux and Android, current status.** The tracker says Nightly-only with Linux
  expected in 2026 [2]; an open tracker issue says the 152 release channel works behind
  `dom.webgpu.enabled` [12]. A Mozilla release note or the Bugzilla meta-bug for the Linux
  ship would resolve the discrepancy.
- **Will Firefox implement compatibility mode?** Safari is effectively settled: the Blink
  intent says it is "not anticipated that this feature will ship in Safari" because all
  shipping Apple devices support core WebGPU, and compatibility-mode apps run unchanged on
  core-only browsers [11]. Firefox is the open half — Mozilla approved the spec changes but
  has not committed to implementing, and neither Gecko nor WebKit has an entry for
  compatibility mode in the standards-positions repos (the "Positive" labels are the intent
  author's reading of Working Group participation) [11]. A Mozilla tracking bug would settle
  it.
- **Safari's known limitations, from Apple.** WebKit's Safari 26.0 notes describe what
  shipped, not what is missing [4]; a WebKit feature-status page or release-note errata would
  be needed to characterise Safari's gaps the way Mozilla characterised Firefox's [3].
- **Are the mobile buffer-size ceilings still current?** A 2025 analysis cites Safari Metal
  buffer limits and Chrome `maxStorageBufferBindingSize` constraints [22]; only current
  measurements across devices, or vendor documentation of adapter limits, would confirm.

## Sources

| n | id | title | url |
|---|---|---|---|
| 1 | 016 | WebGPU is now supported in major browsers (web.dev) | https://web.dev/blog/webgpu-supported-major-browsers |
| 2 | 011 | Implementation Status - gpuweb/gpuweb Wiki | https://github.com/gpuweb/gpuweb/wiki/Implementation-Status |
| 3 | 005 | Shipping WebGPU on Windows in Firefox 141 - Mozilla Gfx Team Blog | https://mozillagfx.wordpress.com/2025/07/15/shipping-webgpu-on-windows-in-firefox-141/ |
| 4 | 008 | WebKit Features in Safari 26.0 | https://webkit.org/blog/17333/webkit-features-in-safari-26-0/ |
| 5 | 006 | WebGPU - Can I use... Support tables for HTML5, CSS3, etc | https://caniuse.com/webgpu |
| 6 | 009 | What's New in WebGPU (Chrome 146) | https://developer.chrome.com/blog/new-in-webgpu-146 |
| 7 | 015 | WebGPU Compatibility Mode (webgpufundamentals.org) | https://webgpufundamentals.org/webgpu/lessons/webgpu-compatibility-mode.html |
| 8 | 003 | Overview of WebGPU (Chrome for Developers) | https://developer.chrome.com/docs/web-platform/webgpu/overview |
| 9 | 001 | WebGPU: Troubleshooting tips and fixes (Chrome for Developers) | https://developer.chrome.com/docs/web-platform/webgpu/troubleshooting-tips |
| 10 | 017 | What's New in WebGPU (Chrome 149-150) | https://developer.chrome.com/blog/new-in-webgpu-149-150 |
| 11 | 018 | Intent to Ship: WebGPU Compatibility mode (blink-dev) | https://groups.google.com/a/chromium.org/g/blink-dev/c/N3RlLGCOTJ4 |
| 12 | 002 | Firefox 152 release channel on Linux support behind about:config flag (gpuweb issue 6331) | https://github.com/gpuweb/gpuweb/issues/6331 |
| 13 | 019 | Firefox Catches Up to Chrome With the Addition of This Feature But Leaves Linux Out (for now) | https://itsfoss.com/news/firefox-webgpu-support/ |
| 14 | 020 | WebGPU Lands in Firefox 141 on Windows, Eyes Linux and macOS Next | https://linuxiac.com/webgpu-lands-in-firefox-141-on-windows-eyes-linux-and-macos-next/ |
| 15 | 010 | What's the story with WebGPU in Firefox? Why is it still not enabled by default? (Hacker News) | https://news.ycombinator.com/item?id=41157383 |
| 16 | 007 | WebGPU Browser Support in 2026: Complete Compatibility Guide | https://webo360solutions.com/blog/webgpu-browser-support/ |
| 17 | 004 | News from WWDC25: WebKit in Safari 26 beta | https://webkit.org/blog/16993/news-from-wwdc25-web-technology-coming-this-fall-in-safari-26-beta/ |
| 18 | 022 | WebKit bug 299510 - "Experimental WebGPU" in Safari 26 @ macOS 15 no longer works with basic examples | https://bugs.webkit.org/show_bug.cgi?id=299510 |
| 19 | 012 | WebGPU backend fails (device lost) on Safari 26 when building to WASM using Emscripten (imgui issue 9103) | https://github.com/ocornut/imgui/issues/9103 |
| 20 | 013 | "shader-f16" requirements exclude all Qualcomm devices (gpuweb issue 5006) | https://github.com/gpuweb/gpuweb/issues/5006 |
| 21 | 014 | WebGPU API - Web APIs (MDN) | https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API |
| 22 | 021 | WebGPU bugs are holding back the browser AI revolution (Medium) | https://medium.com/@marcelo.emmerich/webgpu-bugs-are-holding-back-the-browser-ai-revolution-27d5f8c1dfca |
