# Recording the MANAK-SETU prototype video — Windows guide

Screen **and** webcam in one recording. Three routes below: pick **one**.
If you have never done this before, use Route B (Clipchamp) — it is built into
Windows 11 and needs no install.

---

## Before anything else — set the stage

Do these five things first. They matter more than which tool you pick.

1. **Warm the site.** Open https://manak-setu-h8b0.onrender.com and let it fully
   load. The free host sleeps when idle and the first load is slow. Never film
   the cold start.
2. **Close every other tab.** Whatever is open will be in the video.
3. **Turn on Do Not Disturb.** `Win + N` → Focus assist / Do not disturb. One
   notification popup ruins a take.
4. **Set display scale to 100%** (Settings → System → Display) and put the
   browser **full screen with F11**. Recordings look soft when Windows is scaled
   to 125% or 150%.
5. **Plug in power and use a wired connection if you can.** Laptops throttle on
   battery, and the site is hosted, so a dropout mid-demo means a retake.

---

## Route A — OBS Studio (best quality, ~10 minutes to set up)

Free, no watermark, no time limit, no account. Download from **obsproject.com**.

### Setup

1. Open OBS. If the auto-configuration wizard appears, choose
   **Optimise for recording**.
2. In the **Sources** box at the bottom, click **+** → **Display Capture** →
   OK → pick your monitor → OK. Your screen appears in the canvas.
3. Click **+** again → **Video Capture Device** → OK → under *Device* choose
   your webcam → OK.
4. **Drag the webcam** to a bottom corner. Drag a corner handle inward to shrink
   it to about a quarter of the width. Hold **Alt** to crop instead of scale if
   you want a tighter frame.
5. In the Sources list, make sure **Video Capture Device sits ABOVE Display
   Capture**. If it is below, your face is hidden behind the screen. Drag it up.
6. In the **Audio Mixer**, talk and check that **Mic/Aux** shows moving green
   bars. Flat bars mean the wrong microphone — click the gear → **Properties**
   → choose the right one.

### Recording

Press **Start Recording**, do the demo, press **Stop Recording**.
Files save to `Videos` by default. Change it under **Settings → Output →
Recording Path**, and set **Recording Format to MP4** while you are there —
OBS defaults to MKV, which some editors and upload forms reject.

### If your screen capture is a BLACK rectangle

This is the most common OBS problem on Windows and it is almost always a
dual-GPU laptop (Intel + NVIDIA). Fix it one of these ways:

- **Easiest:** delete the Display Capture source and use **Window Capture**
  instead, pointed at your browser window. This works regardless of GPU.
- **Or:** Windows **Settings → System → Display → Graphics**, find OBS, set it
  to **Power saving** (integrated GPU), then fully restart OBS.

If your **webcam** is black, close Zoom, Teams and any other app that may be
holding the camera — only one app can use it at a time.

---

## Route B — Clipchamp (easiest, already on Windows 11)

Built into Windows 11. It records screen **and** camera together, and edits in
the same app. A free Microsoft account may be requested.

1. Press **Start**, type **Clipchamp**, open it.
2. Choose **Create a new video**.
3. On the left toolbar click **Record & create** → **Screen and camera**.
4. Allow **camera** and **microphone** when prompted.
5. Pick your camera and mic from the dropdowns. Your face appears in a circle in
   the corner — that is exactly what you want.
6. Click the **record button**, then choose what to share: select
   **Entire screen** or the **browser window**, and click **Share**.
7. Do the demo. Click **Stop sharing** when finished.
8. The clip drops onto the timeline. Trim the dead air at the start and end by
   dragging the clip edges.
9. **Export → 1080p.** Save the MP4.

Clipchamp's free tier exports at 1080p with no watermark. Do not add any of the
stock intro templates — a plain recording looks more credible than a video with
animated titles.

---

## Route C — Zoom (fallback, 30 seconds to set up)

If both routes above fight you and time is short, this always works.

1. Open Zoom → **New Meeting** (alone, no one else needed).
2. Turn your **video on**.
3. Click **Share Screen** → choose the browser window → **Share**.
4. Click **Record** → **Record on this Computer**.
5. Do the demo. **Stop Share**, then **End Meeting**.
6. Zoom converts the recording and opens the folder. The MP4 has your screen
   with your face in the corner.

Quality is lower than OBS and the face thumbnail is small, but a finished video
beats a perfect one that never got recorded.

---

## Test before the real take

**Record 15 seconds and watch it back.** Check three things:

- the screen is sharp, and not a black rectangle
- your face is visible and lit from the front
- **the audio is actually there**

Discovering a muted microphone after the real take is the most common way this
goes wrong.

---

## Recording the demo itself

The walkthrough runs on its own — **click "Run demo" in the toolbar** and it
advances through seven steps by itself, about 70 seconds total. Nobody has to
click anything during it. That means the person recording only has to talk.

**Sequence for the take:**

1. Site already loaded and warm, browser full screen (F11)
2. Start recording
3. Two or three sentences of introduction
4. Click **Run demo**
5. Narrate over the seven steps
6. A closing sentence after it finishes
7. Stop recording

**Practise the narration twice against the running demo before recording.** The
step timings are fixed, so you can rehearse to them exactly. Per-step hold times
and suggested narration are in `MANAK-SETU-demo-brief.md`.

**Speak slightly slower than feels natural.** Each step holds 9–11 seconds,
which is roughly 25–30 words at a comfortable pace. Rushing to fit more in is
the most common narration mistake.

---

## Two things that must NOT appear in the video

Both are explained in the demo brief, but they matter enough to repeat:

- **Do not demonstrate multilingual input on the hosted site.** The translation
  provider refuses the shared datacentre IP, so it will show a
  "could not be read" message. It works on a local machine and can be shown live
  to the panel — it just cannot be filmed from the hosted link.
- **Do not claim the clause was written by the AI model.** The hosted version has
  no language model and composes clauses from a deterministic template. The
  interface says so on screen, so claiming otherwise would be contradicted by
  the video itself.

---

## Framing and audio

- **Light from the front.** Sit facing a window or a lamp. A window *behind* you
  turns your face into a silhouette.
- **Camera at eye level.** Stack the laptop on books if needed. A laptop on a
  desk films up your chin.
- **Record somewhere soft** — a room with curtains, a bed, cushions. Bare walls
  and tiled floors produce echo that cannot be fixed afterwards.
- **Wired earphones with a mic beat a laptop microphone**, and are better than
  Bluetooth, which often drops audio quality while recording.
- **Sit still and close to the mic.** Consistent volume matters more than
  expensive equipment.
