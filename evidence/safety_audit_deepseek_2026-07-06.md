# AgentNap Safety Audit — độc lập

**File audited:** `/Users/phuongnam/02.AI/NP_AI_macos/agentnap/agentnap.py` (383 dòng)
**Audit date:** 2026-07-06
**Method:** Đọc toàn bộ source, trace từng đường code kill, phân tích guard và edge case.

---

## Claim 1: "Hành động tự động DUY NHẤT là kill process orphan PPID=1 match agent pattern — không đường code nào khác tự kill"

**VERDICT: PASS**

**Dẫn chứng:**

1. `_terminate(pid, grace)` — hàm kill thực tế (dòng 292–307): gọi `os.kill(pid, SIGTERM)` → chờ grace → `os.kill(pid, SIGKILL)`. Chỉ được gọi từ `reap()` (dòng 273).

2. `reap()` (dòng 273–289): duy nhất được gọi từ 2 nơi:
   - `cmd_reap` (dòng 368): `reap(find_orphans(cfg), grace, apply="--apply" in args)` — user chạy CLI, không tự động.
   - `cmd_daemon` (dòng 347): `reap(orphans, grace, apply=True)` — tự động khi memory pressure ≥ threshold.

3. `cmd_daemon` (dòng 335–352): vòng lặp `while True`:
   - Dòng 342: kiểm tra `level >= daemon_pressure_level`
   - Dòng 343: chỉ gọi `find_orphans()` → reap nếu có orphans
   - Không đường code nào khác trong vòng lặp gọi kill

4. `find_orphans()` (dòng 261–270): filter khớp:
   `ppid == 1` AND `.app/Contents/` NOT in command AND `age_s >= min_age_seconds` AND `rss_mb >= min_rss_mb`

5. `agentnap nap <pid>` (dòng 371–376): gọi `SIGSTOP` (tạm dừng, reversible bằng `agentnap wake` + SIGCONT). Đây là lệnh người dùng chủ động, không tự động, và là suspend chứ không kill.

6. Không có `os.kill`, `subprocess.run(["kill",...)`, `signal.SIGKILL`, `signal.SIGTERM` nào khác trong file.

**Kết luận:** Chỉ có một đường tự động kill: daemon → PPID=1, agent-matched orphans. Không có đường kill nào khác tự động.

---

## Claim 2: "Không bao giờ kill app GUI .app bundle hay process được protect"

**VERDICT: PASS** (với lưu ý)

**Dẫn chứng:**

1. **Bảo vệ .app bundle:**
   - `find_orphans()` dòng 267: `".app/Contents/" not in p["command"]` — loại trừ process mà command path chứa `.app/Contents/` khỏi danh sách reap.
   - `find_idle()` dòng 146 — cùng guard cho advisory.

2. **protect_patterns** (dòng 44):
   - `"agentnap"`, `"Activity Monitor"`, `"loginwindow"` — hardcoded, không bao giờ bị match dù có khớp agent_patterns.
   - Cơ chế: `match_agents()` dòng 254 — duyệt từng process, nếu command chứa bất kỳ protect pattern nào → skip hoàn toàn (không chỉ reap mà còn không hiện trong status/advise).

3. **Substring matching trong protect_patterns** — `"loginwindow"` bảo vệ cả `WindowServer`? Không, `"loginwindow"` không match `WindowServer`. Nhưng `"loginwindow"` bảo vệ process `loginwindow` khỏi mọi false match.

4. **macOS GUI apps trên macOS**: Khi launch dưới dạng .app, command path chứa `.app/Contents/MacOS/` nên bị loại khỏi find_orphans.

**Lưu ý (không phải FAIL):**
- Danh sách protect_patterns mặc định chỉ có 3 entries — rất ngắn. User cần tự thêm nếu có process quan trọng.
- Nếu user chạy `agentnap nap <pid>` (SIGSTOP) với pid của .app bundle, bảo vệ này không có tác dụng vì nap nhận pid trực tiếp, không qua match_agents. Nhưng `nap` là suspend (SIGSTOP/SIGCONT, reversible) chứ không kill.
- Có edge case: process không chứa `.app/Contents/` trong command string nhưng vẫn là macOS app (VD: launch agent ở `~/Library/LaunchAgents/` hoặc XPC service). `find_orphans` sẽ không catch được các process này.

---

## Claim 3: "Reap graceful SIGTERM→grace 8s→SIGKILL, không SIGKILL thẳng"

**VERDICT: PASS**

**Dẫn chứng — `_terminate()` dòng 292–307:**

```python
def _terminate(pid: int, grace: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)          # Bước 1: SIGTERM
    except ProcessLookupError:
        return                                 # Đã chết rồi thì không cần làm gì
    deadline = time.time() + grace
    while time.time() < deadline:
        try:
            os.kill(pid, 0)                    # Bước 2: kiểm tra còn sống?
        except ProcessLookupError:
            return                             # Đã chết sạch, không cần SIGKILL
        time.sleep(0.25)
    try:
        os.kill(pid, signal.SIGKILL)           # Bước 3: chỉ SIGKILL nếu vẫn còn
    except ProcessLookupError:
        pass
```

**Phân tích sequence:**
1. SIGTERM gửi ngay lập tức — process có cơ hội bắt signal, cleanup, exit gracefully.
2. Polling `os.kill(pid, 0)` mỗi 250ms trong `grace` giây (default 8) — kiểm tra process đã tắt chưa, không tốn CPU.
3. SIGKILL chỉ gửi nếu sau grace process vẫn còn sống.
4. Grace period default = 8 giây (config: `grace_seconds`, dòng 45). Đủ cho hầu hết agent cleanup, nhưng có thể ngắn nếu process đang flush dữ liệu lớn.
5. Không đường code nào gọi SIGKILL trực tiếp — luôn có SIGTERM trước.

**Không có path nào gọi signal.SIGKILL mà không qua _terminate()** — grep toàn file cho SIGKILL chỉ thấy ở dòng 305 trong `_terminate`.

---

## Claim 4: "AI advisor chỉ gửi data tới endpoint user tự cấu hình, key chỉ từ env, không hardcode secret"

**VERDICT: PASS**

**Dẫn chứng — `ai_advise()` dòng 199–242:**

1. **API key từ env (dòng 204):**
   ```python
   key = os.environ.get("AGENTNAP_API_KEY")
   ```
   - Không có fallback nào khác (không đọc từ file config, không hardcode string).
   - Nếu key không có → trả message hướng dẫn Export key (dòng 206–210), không crash.

2. **Endpoint user cấu hình (dòng 55, 226):**
   ```python
   "ai_api_base": "https://api.deepseek.com",     # default
   ...
   cfg["ai_api_base"].rstrip("/") + "/chat/completions"
   ```
   - Default là DeepSeek (open, không vendor-lock).
   - User override trong `~/.config/agentnap/config.json` với field `"ai_api_base"`.
   - Hỗ trợ bất kỳ OpenAI-compatible API nào (DeepSeek, OpenAI, Groq, OpenRouter, Ollama local).

3. **Model cấu hình (dòng 56, 212):**
   ```python
   "ai_model": "deepseek-chat"                    # default
   ```
   - User có thể override trong config.json.

4. **Không hardcode secret (scan toàn file):**
   - Không có `"sk-"`, `"api_key"`, `"secret"` string nào ngoài `AGENTNAP_API_KEY` (env var name) và `Authorization: f"Bearer {key}"` (dùng biến từ env).
   - Config file chỉ chứa `ai_api_base` và `ai_model`, không chứa key.
   - File `.env` không được load — key bắt buộc từ environment.

5. **Degrade gracefully (dòng 241–242):** Nếu network error, key sai, timeout → trả message lỗi, không crash, không gửi data đi đâu khác.

---

## Lỗ hổng an toàn — khiến user bị kill nhầm việc đang chạy

### 1. PPID=1 KHÔNG đồng nghĩa "dead work" trên macOS (CAO)

Trên macOS, launchd (PID 1) là parent của nhiều process hợp lệ:
- Terminal bị close nhưng process còn chạy (nohup, disown, background job)
- Service agent launched by launchd
- Process bị `SIGCHLD` không được handle đúng cách

**Kịch bản kill nhầm:**
1. User chạy script dài: `python3 train_claude_model.py &` rồi đóng terminal.
2. Process orphan (PPID=1), đang tính toán, CPU ~100%.
3. Nếu command chứa substring "claude" → khớp agent_pattern.
4. Sau 5 phút → daemon reap nếu pressure ≥ 2.
5. Grace 8s không đủ cho Python model training cleanup → SIGKILL → mất dữ liệu.

**Đánh giá:** Khả năng xảy ra thấp (cần pressure cao + đúng pattern + user không có protect rule), nhưng hậu quả nặng.

### 2. Substring matching — false positive (TRUNG BÌNH)

Pattern matching dùng `pat in command` (dòng 256), không phải exact match:
- `"cursor"` → match `cursor_test_runner.py`, `json_cursor.py`, `cursor_position_tracker`
- `"claude"` → match `claude_analysis_result.csv`, `claude_data_processor.sh`
- `"serena"` → match serena utility script (ngoài serena IDE agent)

**Đánh giá:** User custom script có thể bị match nhầm.

### 3. .app/Contents/ guard chỉ bảo vệ GUI apps (TRUNG BÌNH)

`find_orphans` dòng 267 bảo vệ process có command path chứa `.app/Contents/`. Nhưng:
- **Launch agents** (ở ~/Library/LaunchAgents/) không có .app/Contents/ — vulnerable.
- **CLI tools** của macOS (như `system_profiler`, `mdutil`) — không có .app/Contents/ — low risk vì không match agent_patterns.
- **Daemon/service background process** của third-party software — không có guard.

### 4. Grace period 8s có thể không đủ (THẤP)

`grace_seconds` default = 8 (dòng 45). Với các agent process đang chạy inference hoặc xử lý dữ liệu lớn:
- AI agent đang generate response → SIGTERM → cần save state → 8s không đủ → SIGKILL → mất work.
- Hậu quả là mất unsaved work chứ không phải kill nhầm việc đang chạy (process đã được SIGTERM đúng).

### 5. Daemon mode không có user approval (CAO)

Trong daemon mode (dòng 340–352), khi pressure ≥ threshold:
- `reap(orphans, grace, apply=True)` — không cần --apply, không cần xác nhận.
- User có thể không biết daemon đang chạy reap tự động.
- Notification qua `notify()` (macOS notification) có thể bị miss nếu user không nhìn màn hình.

### 6. protect_patterns rất ngắn (THẤP)

Default chỉ 3 entries. User cần biết tự add nếu có process quan trọng. Nếu không đọc docs, user có thể tin tưởng "never kills active work" mà không biết mình cần cấu hình thêm.

---

## Kết luận: Sản phẩm có dám ship với guarantee "never kills active work" không?

**Verdict: CÓ THỂ SHIP với guarantee hiện tại, nhưng guarantee nên tightened.**

### Lý do có thể ship:
1. **Thiết kế overall tốt**: Chỉ target orphan PPID=1 + agent pattern + 5 guard (age/RSS/.app/protect/substring). Dry-run mặc định. Graceful termination đúng chuẩn.
2. **Rủi ro thấp trong thực tế**: Cần đồng thời (a) daemon active + (b) pressure cao + (c) process trùng agent_pattern + (d) process orphan thật + (e) user không có custom protect rule. Xác suất tổ hợp thấp.
3. **Transparency tốt**: Action luôn log ra stdout, trình bày rõ orphan/list.

### Lý do nên tighten guarantee:
1. **PPID=1 ≠ dead work trên macOS.** Guarantee tuyệt đối "never kills active work" là misleading về mặt kỹ thuật — process có parent chết nhưng vẫn đang làm việc active.
2. **Daemon mode bypass dry-run safeguard.** User reap manual cần `--apply`, nhưng daemon reap thì auto apply — đây là design decision nhưng cần documentation rõ.
3. **Không có confirmation step trong daemon mode.** Nếu user vừa launch agentnap daemon vừa làm việc với agent tool, có thể reap nhầm.

### Khuyến nghị:
1. **Sửa guarantee text** từ `"never kills active work"` thành `"only reaps orphan agent processes whose parent has exited"` — chính xác hơn và vẫn an toàn marketing.
2. **Thêm cơ chế dry-run cho daemon** (VD: vòng daemon đầu tiên chỉ report, user confirm bằng signal mới apply).
3. **Protect patterns mặc định** nên mở rộng: VSCode helpers, Terminal, iTerm2, tmux, SSH.
4. **Tăng grace period** với process RSS > 1GB (cần thêm thời gian cleanup).
5. **Document PPID=1 caveat** rõ trong README.

---

**Claim-by-claim tổng kết:**

| Claim | Verdict | Ghi chú |
|-------|---------|---------|
| (1) Chỉ tự kill orphan PPID=1 match agent | **PASS** | Duy nhất daemon → find_orphans → reap → _terminate |
| (2) Không kill .app bundle / protected | **PASS** | .app/Contents/ guard + protect_patterns. Lưu ý: protect_patterns ngắn; launch agents/XPC không được cover |
| (3) Graceful SIGTERM→grace→SIGKILL | **PASS** | Luôn SIGTERM trước, poll, chỉ SIGKILL khi timeout. Không path nào SIGKILL thẳng |
| (4) AI advisor endpoint user config, key từ env | **PASS** | Key chỉ từ AGENTNAP_API_KEY env; endpoint + model trong config; không hardcode secret |

**Lỗ hổng an toàn chính:** PPID=1 không đồng nghĩa dead work; daemon mode reap auto không cần xác nhận; substring pattern matching có thể false positive.
**Rủi ro tổng thể:** THẤP (với cấu hình mặc định) nhưng guarantee nên tightened.

DONE: Independent safety audit of agentnap.py — 4/4 claims PASS; 6 vulnerabilities found; guarantee text should be tightened.
