/* =========================================
   LIVE / OFF STATUS
========================================= */

function setMeetingLiveStatus(isLive) {

    const status =
        document.querySelector(".meeting-status");

    if (!status) {
        console.log("Meeting status element not found.");
        return;
    }

    const dot =
        status.querySelector(".status-dot");

    if (isLive) {

        // GREEN = LIVE
        status.classList.remove("meeting-off");
        status.classList.add("meeting-live");

        status.innerHTML = `
            <span class="status-dot"></span>
            LIVE
        `;

        console.log("🟢 Meeting is LIVE");

    } else {

        // RED = OFF
        status.classList.remove("meeting-live");
        status.classList.add("meeting-off");

        status.innerHTML = `
            <span class="status-dot"></span>
            OFF
        `;

        console.log("🔴 Meeting is OFF");
    }
}


/* =========================================
   START MEETING
========================================= */

function startMeetingStatus() {

    setMeetingLiveStatus(true);

}


/* =========================================
   END MEETING
========================================= */

function endMeetingStatus() {

    setMeetingLiveStatus(false);

}


/* =========================================
   END MEETING BUTTON
========================================= */

document.addEventListener("DOMContentLoaded", function () {

    const endButton =
        document.querySelector(".end-btn");

    if (endButton) {

        endButton.addEventListener("click", function () {

            endMeetingStatus();

            // Existing meeting leave function
            if (typeof leaveMeeting === "function") {
                leaveMeeting();
            }

        });

    }

    // Meeting page open = LIVE
    startMeetingStatus();

});