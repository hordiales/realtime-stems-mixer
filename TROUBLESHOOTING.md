# Troubleshooting Guide

## IPv4/IPv6 Network Issue on macOS

### Problem
OSC messages are sent but not received by the audio server, causing commands like `instant.bass denmark` to appear successful in the mixer but produce no audio.

### Symptoms
- Mixer shows stem loading successfully (e.g., "📥 Smart loading: bass from Denmark → buffer 1000")
- Mixer shows playback status (e.g., "▶️ 🔄 buffer 1000 | rate: 0.893")
- No audio is heard
- `tcpdump` shows UDP packets being sent to the correct port
- Audio server never shows "📡 OSC RECEIVED" messages

### Root Cause
**IPv4/IPv6 Address Resolution Mismatch**

On macOS, when using `"localhost"` as the hostname:
- **OSC Client** (mixer) resolves `"localhost"` to IPv6 (`::1`) and sends packets via IPv6
- **OSC Server** (audio server) binds to `"localhost"` which may resolve to IPv4 (`127.0.0.1`)
- Result: Client sends IPv6 packets but server only listens on IPv4

This can be confirmed with `tcpdump`:
```bash
sudo tcpdump -i lo0 udp port 57120
# Shows: IP6 localhost.xxxxx > localhost.57120: UDP
#        ^^^ IPv6 traffic but server listening on IPv4
```

### Solution

#### 1. Fix Audio Server Binding
In `audio_server.py`, change the OSC server to bind to all interfaces:

```python
# Before (problematic):
self.osc_server = ThreadingOSCUDPServer(("localhost", self.osc_port), disp)

# After (fixed):
self.osc_server = ThreadingOSCUDPServer(("0.0.0.0", self.osc_port), disp)
```

#### 2. Fix Client Address Resolution  
In `stem_mixer_smart.py`, force IPv4 resolution:

```python
# Before (problematic):
self.sc_client = udp_client.SimpleUDPClient(sc_host, sc_port)

# After (fixed):
sc_host_ipv4 = "127.0.0.1" if sc_host == "localhost" else sc_host
self.sc_client = udp_client.SimpleUDPClient(sc_host_ipv4, sc_port)
```

### Why This Happens on macOS

1. **Dual Stack Networking**: macOS supports both IPv4 and IPv6 simultaneously
2. **Localhost Resolution**: `"localhost"` can resolve to either `127.0.0.1` (IPv4) or `::1` (IPv6)
3. **Python OSC Library**: The python-osc library's client and server may resolve `"localhost"` differently
4. **Default Behavior**: macOS may prefer IPv6 for outbound connections but Python may default to IPv4 for server binding

### Verification

After applying the fix, you should see:
- `tcpdump` showing IPv4 traffic: `IP 127.0.0.1.xxxxx > 127.0.0.1.57120`
- Audio server logging: `📡 OSC RECEIVED: /load_buffer [...]`
- Actual audio playback when using commands like `instant.bass denmark`

### Alternative Solutions

If the above doesn't work, try these alternatives:

1. **Force IPv6 for both client and server**:
   ```python
   # Server: bind to IPv6
   self.osc_server = ThreadingOSCUDPServer(("::", self.osc_port), disp)
   # Client: use IPv6 localhost
   self.sc_client = udp_client.SimpleUDPClient("::1", sc_port)
   ```

2. **Disable IPv6 system-wide** (not recommended):
   ```bash
   # Temporarily disable IPv6 (requires restart)
   sudo sysctl -w net.inet6.ip6.disable=1
   ```

3. **Use explicit IP addresses everywhere**:
   - Replace all instances of `"localhost"` with `"127.0.0.1"`
   - Ensures consistent IPv4 usage

### Related Issues

This issue may also affect:
- Other OSC-based applications on macOS
- Python applications using socket libraries with `"localhost"`
- Docker containers with networking issues on macOS
- Any client-server communication relying on localhost resolution

### Prevention

For future projects:
- Always use explicit IP addresses (`127.0.0.1`, `::1`) instead of `"localhost"`
- Test network communication with `tcpdump` or `netstat`
- Consider binding servers to `0.0.0.0` (all IPv4) or `::` (all IPv6)
- Document network requirements clearly