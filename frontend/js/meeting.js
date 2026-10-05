let socket;

let username =
    sessionStorage.getItem("meetingUsername") ||
    prompt("Enter your name:") ||
    "Guest";

sessionStorage.setItem("meetingUsername", username);


// ======================================================
// WEBSOCKET CONNECTION
// ======================================================

function connect() {

    socket = new WebSocket("ws://127.0.0.1:8000/ws");

    socket.onopen = function () {

        console.log("✅ Connected to meeting server");

        socket.send(username);

        setSpeechStatus(
            "idle",
            "Meeting connection is ready."
        );
    };


    socket.onmessage = function (event) {

        const data = JSON.parse(event.data);

        console.log("Server message:", data);

        handleServerMessage(data);
    };


    socket.onclose = function () {

        console.log("❌ WebSocket disconnected");

        setSpeechStatus(
            "idle",
            "Disconnected from meeting server."
        );
    };


    socket.onerror = function (error) {

        console.log("WebSocket error:", error);

        setSpeechStatus(
            "idle",
            "Unable to connect to the meeting server."
        );
    };
}


// ======================================================
// SERVER MESSAGE
// ======================================================

function handleServerMessage(data) {

    if (data.type === "message") {

        addMessage(
            data.username,
            data.message
        );
    }


    if (data.type === "join") {

        addMessage(
            "System",
            data.message
        );

        updateOnlineUsers(
            data.online_users
        );

    }


    if (data.type === "leave") {

        addMessage(
            "System",
            data.message
        );

        updateOnlineUsers(
            data.online_users
        );
    }


    if (data.type === "ai_suggestion") {

        showAIResult(data);
    }

    if (data.type === "topic_update") {
        const topic = document.getElementById("topic");
        if (topic) {
            topic.textContent = data.topic;
        }
    }
}


// ======================================================
// ADD MESSAGE TO LIVE TRANSCRIPT
// ======================================================

function addMessage(author, message) {

    const messages =
        document.getElementById("messages");

    if (!messages) {
        return;
    }


    const box =
        document.createElement("div");

    box.className = "message";


    const name =
        document.createElement("strong");

    name.textContent =
        `${author}:`;


    const text =
        document.createElement("p");

    text.textContent =
        message;


    box.appendChild(name);

    box.appendChild(text);

    messages.appendChild(box);


    messages.scrollTop =
        messages.scrollHeight;
}


// ======================================================
// AI RESULT
// ======================================================

function showAIResult(data) {

    const suggestion =
        document.getElementById("aiSuggestion");

    const answer =
        document.getElementById("aiAnswer");

    const topic =
        document.getElementById("topic");

    const question =
        document.getElementById("questionDetected");


    if (suggestion) {

        suggestion.textContent =
            data.suggestion ||
            "No suggestion available.";
    }


    if (answer) {

        answer.textContent =
            data.answer ||
            "No answer available.";
    }


    if (topic) {

        topic.textContent =
            data.topic ||
            "General Discussion";
    }


    if (question) {

        question.textContent =
            data.is_question
                ? "Yes"
                : "No";
    }
}


// ======================================================
// ONLINE USERS
// ======================================================

function updateOnlineUsers(count) {

    const onlineCount =
        document.getElementById("onlineCount");

    if (onlineCount) {

        onlineCount.textContent =
            `${count} Online`;
    }
}


// ======================================================
// PARTICIPANT
// ======================================================

// ======================================================
// CHECK WEBSOCKET
// ======================================================

function isMeetingConnected() {

    return (
        socket &&
        socket.readyState === WebSocket.OPEN
    );
}


// ======================================================
// SEND TEXT TO MEETING
// ======================================================

function sendTextToMeeting(message, speaker = null) {

    if (!message) {

        return false;
    }


    if (!isMeetingConnected()) {

        console.log(
            "WebSocket is not ready."
        );


        setSpeechStatus(
            "idle",
            "Meeting connection is not ready."
        );

        return false;
    }


    console.log(
        "Sending meeting message:",
        message
    );


    socket.send(speaker ? JSON.stringify({ message, speaker }) : message);

    return true;
}


// ======================================================
// SEND MANUAL MESSAGE
// ======================================================

function sendMessage() {

    const input =
        document.getElementById(
            "messageInput"
        );


    if (!input) {
        return;
    }


    const message =
        input.value.trim();


    if (
        sendTextToMeeting(message)
    ) {

        input.value = "";
    }
}


// ======================================================
// ENTER KEY
// ======================================================

function handleEnter(event) {

    if (event.key === "Enter") {

        sendMessage();
    }
}


// ======================================================
// PYTHON SPEECH
// ======================================================
// ======================================================
// CONTINUOUS SPEECH CONTROL
// ======================================================

let speechActive = false;


// ======================================================
// START / STOP TOGGLE
// ======================================================

function togglePythonSpeaking() {

    if (speechActive) {

        stopPythonSpeaking();

    } else {

        startPythonSpeaking();
    }
}


// ======================================================
// START PYTHON SPEECH
// ======================================================

function startPythonSpeaking() {

    if (!isMeetingConnected()) {

        setSpeechStatus(
            "idle",
            "Please wait. Meeting connection is not ready."
        );

        return;
    }


    if (
        !window.pywebview ||
        !window.pywebview.api
    ) {

        setSpeechStatus(
            "idle",
            "Python microphone is available only in the desktop companion."
        );

        return;
    }


    console.log(
        "🎤 Starting continuous microphone..."
    );


    speechActive = true;


    setSpeechStatus(
        "listening",
        "Listening continuously… speak normally."
    );


    window.pywebview.api
        .start_speaking()

        .then(function(result) {

            console.log(
                "Python speech result:",
                result
            );


            if (
                result &&
                result.started === false
            ) {

                speechActive = false;

                setSpeechStatus(
                    "idle",
                    result.message ||
                    "Unable to start microphone."
                );
            }

        })

        .catch(function(error) {

            console.error(
                "Python speech error:",
                error
            );


            speechActive = false;


            setSpeechStatus(
                "idle",
                "Unable to start microphone input."
            );
        });
}


// ======================================================
// STOP PYTHON SPEECH
// ======================================================

function stopPythonSpeaking() {

    if (
        !window.pywebview ||
        !window.pywebview.api
    ) {

        return;
    }


    console.log(
        "⏹ Stopping continuous microphone..."
    );


    speechActive = false;


    window.pywebview.api
        .stop_speaking()

        .then(function(result) {

            console.log(
                "Python stop result:",
                result
            );


            setSpeechStatus(
                "idle",
                "Microphone stopped."
            );

        })

        .catch(function(error) {

            console.error(
                "Python stop error:",
                error
            );


            setSpeechStatus(
                "idle",
                "Microphone stopped."
            );
        });
}


// ======================================================
// RECEIVE SPEECH FROM PYTHON
// ======================================================

function receiveSpeechTranscript(text) {

    console.log(
        "🎤 Speech chunk received:",
        text
    );


    if (!text || !text.trim()) {

        return;
    }


    /*
     * Send every speech chunk through
     * the existing WebSocket.
     */

    if (
        sendTextToMeeting(
            text.trim()
        )
    ) {

        /*
         * Keep listening state.
         * Do NOT change the button back to
         * Start Speaking after every chunk.
         */

        setSpeechStatus(
            "listening",
            "Listening continuously…"
        );
    }
}


// ======================================================
// SPEECH STATUS
// ======================================================
function setSpeechStatus(state, message) {

    const status = document.getElementById("speechStatus");
    const button = document.getElementById("speechButton");

    // Status message
    if (status) {
        status.textContent = message || "";
    }

    if (!button) {
        return;
    }

    // Processing
    if (state === "processing") {

        button.textContent = "⏳";
        button.title = "Processing speech...";
        button.disabled = true;

        return;
    }

    // Listening
    if (speechActive) {

        button.textContent = "⏹";
        button.title = "Stop Speaking";
        button.disabled = false;

        return;
    }

    // Ready / Stopped
    button.textContent = "🎤";
    button.title = "Start Speaking";
    button.disabled = false;
}

// ======================================================
// SUMMARY
// ======================================================

async function getSummary() {

    try {

        const response =
            await fetch(
                "http://127.0.0.1:8000/meeting/summary",
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        alert(data.summary);

    } catch (error) {

        console.error(
            "Summary error:",
            error
        );


        alert(
            "Unable to generate meeting summary."
        );
    }
}


// ======================================================
// LEAVE MEETING
// ======================================================

function leaveMeeting() {

    stopPythonSpeaking();
    if (systemAudioActive && window.pywebview && window.pywebview.api) {
        window.pywebview.api.stop_system_audio();
    }

    if (socket) {

        socket.close();
    }


    sessionStorage.removeItem(
        "meetingUsername"
    );


    window.location.href =
        "index.html";
}


// ======================================================
// MEETING HISTORY
// ======================================================

async function loadMeetingHistory() {

    const history =
        document.getElementById(
            "meetingHistory"
        );


    if (!history) {
        return;
    }


    try {

        const response =
            await fetch(
                "http://127.0.0.1:8000/meetings"
            );


        const data =
            await response.json();


        history.replaceChildren();


        if (!data.meetings.length) {

            history.textContent =
                "No meetings found.";

            return;
        }


        data.meetings.forEach(
            function(meeting) {

                const card =
                    document.createElement(
                        "div"
                    );


                card.className =
                    "meeting-card";


                card.innerHTML = `
                    <div>
                        <h3></h3>
                        <p></p>
                        <p></p>
                    </div>

                    <button>
                        View Meeting
                    </button>
                `;


                card.querySelector(
                    "h3"
                ).textContent =
                    meeting.title;


                card.querySelectorAll(
                    "p"
                )[0].textContent =
                    `Meeting ID: ${meeting.id}`;


                card.querySelectorAll(
                    "p"
                )[1].textContent =
                    meeting.created_at;


                card.querySelector(
                    "button"
                ).onclick =
                    function() {

                        viewMeeting(
                            meeting.id
                        );
                    };


                history.appendChild(
                    card
                );
            }
        );

    } catch (error) {

        console.error(
            "Meeting history error:",
            error
        );


        history.textContent =
            "Unable to load meeting history.";
    }
}


// ======================================================
// VIEW MEETING
// ======================================================

async function viewMeeting(id) {

    try {

        const response =
            await fetch(
                `http://127.0.0.1:8000/meetings/${id}`
            );


        const data =
            await response.json();


        if (data.error) {

            alert(data.error);

            return;
        }


        sessionStorage.setItem(
            "selectedMeeting",
            JSON.stringify(data)
        );


        window.location.href =
            "meeting-history.html";

    } catch (error) {

        console.error(
            "Meeting details error:",
            error
        );


        alert(
            "Unable to load meeting details."
        );
    }
}


// ======================================================
// START
// ======================================================

connect();


if (
    document.getElementById(
        "meetingHistory"
    )
) {

    loadMeetingHistory();
}

/* =========================================
   COMPACT MEETING HISTORY
========================================= */

async function toggleMeetingHistory() {

    let panel = document.getElementById("historyOverlay");

    // If history is already open, close it
    if (panel) {
        panel.remove();
        return;
    }

    // Create history overlay
    panel = document.createElement("div");

    panel.id = "historyOverlay";
    panel.className = "history-overlay";

    panel.innerHTML = `
        <div class="history-topbar">

            <div>
                <h2>🕘 Meeting History</h2>
                <span>Previous meetings</span>
            </div>

            <button
                class="history-close-btn"
                onclick="toggleMeetingHistory()">
                ×
            </button>

        </div>

        <div
            id="compactMeetingHistory"
            class="compact-meeting-history">

            <div class="history-loading">
                Loading meetings...
            </div>

        </div>

        <button
            class="back-meeting-btn"
            onclick="toggleMeetingHistory()">

            ← Back to Meeting

        </button>
    `;

    // Put overlay directly inside the main compact window
    const meetingWindow =
        document.querySelector(".meeting-window");

    if (!meetingWindow) {
        console.error("Meeting window not found.");
        return;
    }

    meetingWindow.appendChild(panel);

    // Load meetings
    await loadCompactMeetingHistory();
}


/* =========================================
   LOAD MEETING HISTORY
========================================= */

async function loadCompactMeetingHistory() {

    const history =
        document.getElementById(
            "compactMeetingHistory"
        );

    if (!history) {
        return;
    }

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/meetings"
        );

        if (!response.ok) {
            throw new Error(
                "Failed to load meetings"
            );
        }

        const data = await response.json();

        history.replaceChildren();

        if (
            !data.meetings ||
            data.meetings.length === 0
        ) {

            const empty =
                document.createElement("div");

            empty.className =
                "history-empty";

            empty.textContent =
                "No meetings found.";

            history.appendChild(empty);

            return;
        }

        data.meetings.forEach(function (meeting) {

            const card =
                document.createElement("div");

            card.className =
                "compact-history-card";


            /* Meeting information */

            const info =
                document.createElement("div");

            info.className =
                "history-card-info";


            const title =
                document.createElement("h3");

            title.textContent =
                meeting.title ||
                "AI Meeting";


            const meetingId =
                document.createElement("p");

            meetingId.textContent =
                `Meeting ID: ${meeting.id}`;


            const time =
                document.createElement("p");

            time.textContent =
                meeting.created_at ||
                "Time unavailable";


            info.appendChild(title);
            info.appendChild(meetingId);
            info.appendChild(time);


            /* View button */

            const viewButton =
                document.createElement("button");

            viewButton.className =
                "view-history-btn";

            viewButton.textContent =
                "View →";


            viewButton.onclick =
                function () {

                    viewCompactMeeting(
                        meeting.id
                    );

                };


            card.appendChild(info);

            card.appendChild(viewButton);

            history.appendChild(card);

        });

    } catch (error) {

        console.error(
            "Meeting history error:",
            error
        );

        history.innerHTML = `
            <div class="history-error">
                Unable to load meeting history.
            </div>
        `;
    }
}


/* =========================================
   VIEW SELECTED MEETING
========================================= */

async function viewCompactMeeting(meetingId) {

    try {

        const response = await fetch(
            `http://127.0.0.1:8000/meetings/${meetingId}`
        );

        const data = await response.json();

        if (data.error) {

            alert(data.error);

            return;
        }

        sessionStorage.setItem("selectedMeeting", JSON.stringify(data));
        showCompactMeetingDetails(data);

    } catch (error) {

        console.error(
            "Meeting details error:",
            error
        );

        alert(
            "Unable to load meeting details."
        );
    }
}


function showCompactMeetingDetails(data) {

    const panel = document.getElementById("historyOverlay");
    if (!panel || !data || !data.meeting) {
        return;
    }

    panel.replaceChildren();

    const topbar = document.createElement("div");
    topbar.className = "history-topbar";

    const backButton = document.createElement("button");
    backButton.className = "history-back-btn";
    backButton.textContent = "← Back";
    backButton.onclick = showCompactMeetingHistory;

    const heading = document.createElement("h2");
    heading.textContent = "Meeting Details";

    const closeButton = document.createElement("button");
    closeButton.className = "history-close-btn";
    closeButton.textContent = "×";
    closeButton.title = "Close meeting history";
    closeButton.onclick = toggleMeetingHistory;

    topbar.append(backButton, heading, closeButton);

    const content = document.createElement("div");
    content.className = "compact-meeting-details";

    const info = document.createElement("section");
    info.className = "detail-section";
    info.innerHTML = "<h3>Meeting Information</h3>";
    [["Title", data.meeting.title], ["Meeting ID", data.meeting.id], ["Date", data.meeting.created_at]].forEach(([label, value]) => {
        const line = document.createElement("p");
        const strong = document.createElement("strong");
        strong.textContent = `${label}: `;
        line.append(strong, document.createTextNode(value || "Not available"));
        info.appendChild(line);
    });

    const participants = document.createElement("section");
    participants.className = "detail-section";
    participants.innerHTML = "<h3>Participants</h3>";
    const names = (data.participants || []).map((participant) => participant.username).filter(Boolean);
    const participantText = document.createElement("p");
    participantText.textContent = names.length ? names.join(", ") : "No participants recorded.";
    participants.appendChild(participantText);

    const questions = (data.messages || []).filter((message) => /\?|^(what|why|how|when|where|who|which|can|could|would|should|is|are|do|does|did|will)\b/i.test(message.message || ""));
    const questionSection = document.createElement("section");
    questionSection.className = "detail-section";
    questionSection.innerHTML = "<h3>Questions Discussed</h3>";
    const questionText = document.createElement("p");
    questionText.textContent = questions.length
        ? questions.map((message) => `${message.username}: ${message.message}`).join("\n")
        : "No questions detected in the stored transcript.";
    questionText.className = "detail-pre";
    questionSection.appendChild(questionText);

    if (data.meeting.summary) {
        const summary = document.createElement("section");
        summary.className = "detail-section";
        summary.innerHTML = "<h3>Meeting Summary</h3>";
        const summaryText = document.createElement("p");
        summaryText.className = "detail-pre";
        summaryText.textContent = data.meeting.summary;
        summary.appendChild(summaryText);
        content.append(info, participants, questionSection, summary);
    } else {
        content.append(info, participants, questionSection);
    }

    const transcript = document.createElement("section");
    transcript.className = "detail-section transcript-details";
    transcript.innerHTML = "<h3>Complete Transcript</h3>";
    const messages = data.messages || [];
    if (!messages.length) {
        const empty = document.createElement("p");
        empty.textContent = "No transcript messages were stored for this meeting.";
        transcript.appendChild(empty);
    }
    messages.forEach((message) => {
        const row = document.createElement("article");
        row.className = "detail-message";
        const speaker = document.createElement("strong");
        speaker.textContent = `${message.username || "Unknown"}: `;
        const body = document.createElement("span");
        body.textContent = message.message || "";
        const timestamp = document.createElement("time");
        timestamp.textContent = message.created_at || "";
        row.append(speaker, body, timestamp);
        transcript.appendChild(row);
    });
    content.appendChild(transcript);
    panel.append(topbar, content);
}


function showCompactMeetingHistory() {
    const panel = document.getElementById("historyOverlay");
    if (!panel) {
        return;
    }
    panel.innerHTML = `
        <div class="history-topbar">
            <div><h2>Meeting History</h2><span>Previous meetings</span></div>
            <button class="history-close-btn" onclick="toggleMeetingHistory()" title="Close meeting history">×</button>
        </div>
        <div id="compactMeetingHistory" class="compact-meeting-history"><div class="history-loading">Loading meetings...</div></div>
        <button class="back-meeting-btn" onclick="toggleMeetingHistory()">← Back to Meeting</button>`;
    loadCompactMeetingHistory();
}


/* =========================================
   THREE DOT MENU
========================================= */

function toggleMenu() {

    const menu =
        document.getElementById("meetingMenu");

    if (!menu) {
        return;
    }

    menu.classList.toggle("active");
}


function closeMenu() {

    const menu =
        document.getElementById("meetingMenu");

    if (menu) {

        menu.classList.remove("active");

    }
}


/* =========================================
   HISTORY
========================================= */

function openHistoryFromMenu() {

    closeMenu();

    toggleMeetingHistory();

}


/* =========================================
   ACTION ITEMS
========================================= */

function showActionItems() {

    fetch("http://127.0.0.1:8000/meeting/action-items")
        .then((response) => response.ok ? response.json() : Promise.reject())
        .then((data) => {
            const items = data.action_items || [];
            alert(items.length
                ? "Action Items:\n\n" + items.map((item) => `${item.speaker}: ${item.text}`).join("\n\n")
                : "No action items detected yet.");
        })
        .catch(() => alert("Unable to load action items."));

    return;

}


/* =========================================
   TOPIC
========================================= */

function showDetectedTopic() {

    const topic =
        document.getElementById("topic");

    const value =
        topic
            ? topic.textContent.trim()
            : "No topic detected";

    alert(
        "Detected Topic:\n\n" + value
    );

}


/* =========================================
   LEAVE
========================================= */

function leaveFromMenu() {

    closeMenu();

    leaveMeeting();

}


let systemAudioActive = false;

function toggleSystemAudio() {

    if (!window.pywebview || !pywebview.api) {
        console.error("pywebview API not available");
        return;
    }

    if (!systemAudioActive) {

        pywebview.api.start_system_audio()
            .then((result) => {

                console.log("System audio:", result);

                if (result && result.started) {
                    systemAudioActive = true;

                    const button =
                        document.getElementById("systemAudioButton");

                    if (button) {
                        button.textContent = "⏹";
                        button.title = "Stop Meeting Audio";
                    }
                }

            })
            .catch((error) => {
                console.error(
                    "System audio start error:",
                    error
                );
            });

    } else {

        pywebview.api.stop_system_audio()
            .then((result) => {

                console.log("System audio:", result);

                systemAudioActive = false;

                const button =
                    document.getElementById("systemAudioButton");

                if (button) {
                    button.textContent = "🎧";
                    button.title = "Start Meeting Audio";
                }

            })
            .catch((error) => {
                console.error(
                    "System audio stop error:",
                    error
                );
            });
    }
}

function receiveSystemAudioTranscript(speaker, text) {

    console.log("🎧", speaker, text);

    if (!text) {
        return;
    }

    // Persist and analyze meeting audio through the existing live channel.
    sendTextToMeeting(text.trim(), speaker || "Meeting Speaker");
    return;

    const messages = document.getElementById("messages");

    if (!messages) {
        console.error(
            "Transcript container #messages not found."
        );
        return;
    }

    const message = document.createElement("div");

    message.className =
        "message system-audio-message";

    message.innerHTML = `
        <strong>🎧 ${escapeHtml(speaker)}</strong>
        <p>${escapeHtml(text)}</p>
    `;

    messages.appendChild(message);

    messages.scrollTop =
        messages.scrollHeight;
}


function setSystemAudioStatus(state, message) {

    console.log(
        "System audio status:",
        state,
        message
    );
}


function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}
