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

        updateParticipant(
            data.username
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

function updateParticipant(name) {

    const id =
        `participant-${name}`;

    if (document.getElementById(id)) {
        return;
    }


    const participant =
        document.createElement("div");

    participant.className =
        "participant";

    participant.id =
        id;


    participant.innerHTML = `
        <div class="avatar"></div>
        <h3></h3>
        <p>Online</p>
    `;


    participant
        .querySelector(".avatar")
        .textContent =
        name.charAt(0).toUpperCase();


    participant
        .querySelector("h3")
        .textContent =
        name;


    const participants =
        document.getElementById(
            "participants"
        );


    if (participants) {

        participants.appendChild(
            participant
        );
    }
}


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

function sendTextToMeeting(message) {

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


    socket.send(message);

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

    alert(
        "Action Items feature will be added next."
    );

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