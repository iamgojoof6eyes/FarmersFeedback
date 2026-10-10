# To Do & Implementation Status

## For WhatsApp Nudge & Feedback Pipeline

- [x] **Cron job for sending nudges exclusively to unresponded farmers with Yes/No buttons**
  - **Implementation**: Background APScheduler daemon configured in [`helpers/scheduler.py`](file:///c:/Dev/FarmersFeedback/helpers/scheduler.py#L43-L54) and [`helpers/session_pipeline.py`](file:///c:/Dev/FarmersFeedback/helpers/session_pipeline.py) (`run_unresponded_farmer_nudge_cron`).
  - **Schedule**: Scheduled daily at **7:00 PM IST (19:00)** and **9:00 PM IST (21:00)** (`Asia/Kolkata` timezone).
  - **Function**: Exclusively filters `ongoing_farmer_sessions` where `has_responded != True`, dispatches the feedback prompt message equipped with interactive **Yes / No** (`👍 हाँ / Yes` & `👎 नहीं / No`) buttons, increments `nudge_count`, and updates status to `NUDGED`. Does *not* push feedback in cron because feedback is pushed immediately upon receipt.
  - **Manual Trigger Endpoint**: `POST /api/whatsapp/nudge/cron/run-now`

- [x] **Farmer question answering via GDB knowledge base entries**
  - **Implementation**: [`backend/app/routers/whatsapp.py`](file:///c:/Dev/FarmersFeedback/backend/app/routers/whatsapp.py#L126-L165) (`POST /api/whatsapp/ask-question`) and [`helpers/whatsapp_service.py`](file:///c:/Dev/FarmersFeedback/helpers/whatsapp_service.py).
  - **Function**: Semantic query matcher (`find_best_gdb_match`) maps farmer queries to verified GDB advisory entries, returns certified Hindi & English answers, and creates an ongoing session with `status: "AWAITING_FEEDBACK"`.

- [x] **Farmer feedback capture & immediate GDB rating push**
  - **Implementation**: [`backend/app/routers/whatsapp.py`](file:///c:/Dev/FarmersFeedback/backend/app/routers/whatsapp.py#L184-L203) (`POST /api/whatsapp/submit-feedback`), [`helpers/twilio_service.py`](file:///c:/Dev/FarmersFeedback/helpers/twilio_service.py), and [`helpers/session_pipeline.py`](file:///c:/Dev/FarmersFeedback/helpers/session_pipeline.py#L71-L130) (`record_farmer_feedback_response` with `auto_push_to_gdb=True`).
  - **Function**: As soon as farmer gives feedback (via 1-tap Yes/No Quick Reply buttons or text), the rating is **immediately pushed to the corresponding GDB entry** (updating upvotes/downvotes, helpful ratio, drift detection threshold evaluation), logged to `farmer_feedback`, and the session is cleared from `ongoing_farmer_sessions`. No cron job is required for pushing ratings.

- [x] **Database collection for ongoing farmer question sessions with feedback push & delete lifecycle**
  - **Implementation**: MongoDB collection `ongoing_farmer_sessions` in [`helpers/session_pipeline.py`](file:///c:/Dev/FarmersFeedback/helpers/session_pipeline.py#L10).
  - **Lifecycle**:
    1. Query submitted $\rightarrow$ session stored in `ongoing_farmer_sessions`.
    2. Farmer responds with feedback $\rightarrow$ rating **immediately pushed to GDB entry** (increments `upvotes`/`downvotes`, updates `helpful_ratio`, evaluates statistical flagging threshold, logs to `farmer_feedback`), and **deletes the completed document from `ongoing_farmer_sessions`**.
    3. Unresponded sessions remain in `ongoing_farmer_sessions` and receive the 7PM & 9PM IST cron reminders with Yes/No buttons.
  - **Cleanup & Push Functions**: `push_feedback_to_gdb()` and `push_all_pending_feedback_to_gdb()`.

- [x] **Pure questions (inquiries without feedback) not counted as feedback**
  - **Implementation**: Pure questions remain with `has_responded: False` and `rating: None`.
  - **Rule**: Inquiries remain uncounted until farmer submits rating. GDB metrics and `farmer_feedback` records are only created when feedback rating is submitted.

- [x] **Immediate GDB Push on Feedback vs. Unresponded Farmer Cron Job**
  - **1. Immediate Push on Feedback Receipt**:
    - Triggers as soon as the farmer clicks a Yes/No Quick Reply button or submits feedback via WhatsApp/API.
    - Updates GDB metrics instantly in real time and deletes the session from `ongoing_farmer_sessions`.
  - **2. Unresponded Farmer Cron Job**:
    - Runs at **7:00 PM IST** and **9:00 PM IST** daily via APScheduler (`run_unresponded_farmer_nudge_cron`).
    - Exclusively sends feedback reminder messages with Yes/No interactive buttons to farmers who have *not* given feedback yet.

- [x] **WhatsApp notification to farmer when feedback is pushed manually**
  - **Implementation**: [`helpers/session_pipeline.py`](file:///c:/Dev/FarmersFeedback/helpers/session_pipeline.py#L199-L215) and [`helpers/twilio_service.py`](file:///c:/Dev/FarmersFeedback/helpers/twilio_service.py#L28-L135).
  - **Notification**: When `is_manual=True`, a personalized acknowledgment message is dispatched to the farmer's WhatsApp:
    *"🙏 नमस्ते किसान भाई! आपकी फसल ({crop}) के संबंध में दी गई प्रतिक्रिया AjraSakha GDB ज्ञानकोष में सफलतापूर्वक दर्ज कर ली गई है... 🌱"*
  - **Tracking**: Logged in `twilio_logs` collection with `message_type: "FEEDBACK_ACK_MANUAL"`.

- [x] **Simulation without Twilio for test and presentation purposes**
  - **Implementation**:
    - **Backend Simulation Gateway**: [`helpers/twilio_service.py`](file:///c:/Dev/FarmersFeedback/helpers/twilio_service.py#L116-L135) automatically runs in sandbox/simulation mode if Twilio credentials are not configured, generates simulated message SIDs (`SM_SIM_...`), and logs full incoming/outgoing messages in MongoDB `twilio_logs`.
    - **Frontend Presentation Lab**: [`TwilioWhatsAppView.tsx`](file:///c:/Dev/FarmersFeedback/frontend/src/components/TwilioWhatsAppView.tsx) provides:
      - **Tab 1: Interactive Simulation Lab**: 4-step wizard for live presentations (1. Ask Question $\rightarrow$ 2. Evening Nudge $\rightarrow$ 3. Feedback Response $\rightarrow$ 4. Push to GDB & Farmer WhatsApp Receipt).
      - **Tab 2: Active Ongoing Sessions Monitor**: Real-time table view of `ongoing_farmer_sessions` with live status badges, individual nudge and push triggers.
      - **Tab 3: Cron Automation Control Center**: APScheduler live diagnostic monitor (7:00 PM & 9:00 PM IST) with manual run trigger.
      - **Tab 4: Live Gateway & Webhook Simulator**: Realistic incoming/outgoing message inspector.
      - **WhatsApp Mobile Phone Simulator**: Component in [`WhatsAppSimulator.tsx`](file:///c:/Dev/FarmersFeedback/frontend/src/components/WhatsAppSimulator.tsx) simulating authentic iOS/Android WhatsApp chat bubble interactions with quick-reply buttons and voice note processing.
      - **Answer-First Rating Interaction**: In both the Simulation Lab and Mobile WhatsApp Simulator, asking an agricultural question first renders the certified GDB response answer bubble/card, followed by a separate 1-tap rating prompt (`👍 1: Helpful` / `👎 2: Unhelpful`), rather than bundling them or immediately jumping to feedback capture.
      - **Dynamic Multi-Crop Semantic Matching**: In [`helpers/whatsapp_service.py`](file:///c:/Dev/FarmersFeedback/helpers/whatsapp_service.py#L39-L103), replaced naive regex search with token-level relevance scoring (crop, sub-domain disease/pest, and question weights) across all crops in GDB (Mustard, Paddy, Cotton, Sugarcane, Soybean, Gram, Wheat). Removed hardcoded crop dropdown from Step 1 inquiry form in [`TwilioWhatsAppView.tsx`](file:///c:/Dev/FarmersFeedback/frontend/src/components/TwilioWhatsAppView.tsx#L790-L840) to support questions across any crop seamlessly.
      - **Twilio WhatsApp Quick Reply Buttons & Direct Feedback State Updating**: In [`helpers/twilio_service.py`](file:///c:/Dev/FarmersFeedback/helpers/twilio_service.py) and [`backend/app/routers/whatsapp.py`](file:///c:/Dev/FarmersFeedback/backend/app/routers/whatsapp.py), outgoing GDB answers and leisure nudges are dispatched with structured Quick Reply buttons (`[1️⃣ 👍 1: उपयोगी (Helpful)]` and `[2️⃣ 👎 2: सुधार चाहिए (Unhelpful)]`). When the webhook receives the button payload or 1-tap response, it directly updates the session in `ongoing_farmer_sessions` to `FEEDBACK_RECEIVED` without requiring manual review or text review parsing, while still maintaining the Twilio webhook listener to capture the user's button action. Tab 4 and the audit log now feature interactive 1-tap button simulators and badge indicators.