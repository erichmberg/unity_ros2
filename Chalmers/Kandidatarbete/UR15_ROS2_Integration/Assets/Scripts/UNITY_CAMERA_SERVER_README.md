# Unity Camera HTTP Server (No scene binding)

`UnityCameraHttpServer.cs` auto-creates itself at runtime and streams `MainCamera`.

## Endpoints
- `http://<unity-host-ip>:18082/frame.jpg` (single snapshot)
- `http://<unity-host-ip>:18082/stream.mjpg` (live stream)
- `http://<unity-host-ip>:18082/healthz`

## How to use
1. Keep script in `Assets/Scripts/`.
2. Ensure your scene has one camera tagged `MainCamera`.
3. Press Play in Unity.
4. Open: `http://<your-laptop-ip>:18082/frame.jpg`

No manual GameObject/component assignment needed.

## Notes
- Chosen port `18082` to avoid reserved ports in this project.
- If endpoint returns `no frame yet`, wait 1-2 seconds after Play starts.
