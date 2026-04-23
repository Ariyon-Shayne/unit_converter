document.addEventListener("DOMContentLoaded", function() {
    // Create the timer element
    const timerDiv = document.createElement("div");
    timerDiv.style.position = "fixed";
    timerDiv.style.top = "15px";
    timerDiv.style.right = "20px";
    timerDiv.style.backgroundColor = "rgba(0, 0, 0, 0.7)";
    timerDiv.style.color = "#fff";
    timerDiv.style.padding = "8px 12px";
    timerDiv.style.borderRadius = "8px";
    timerDiv.style.fontFamily = "monospace";
    timerDiv.style.fontSize = "14px";
    timerDiv.style.zIndex = "9999";
    timerDiv.style.boxShadow = "0 2px 4px rgba(0,0,0,0.2)";
    timerDiv.innerHTML = "Session: <span id='session-timer'>05:00</span>";
    document.body.appendChild(timerDiv);

    const timeDisplay = document.getElementById("session-timer");
    
    // 5 minutes in milliseconds
    const SESSION_DURATION = 5 * 60 * 1000;
    
    let sessionEndTime = localStorage.getItem('sessionEndTime');
    if (!sessionEndTime) {
        sessionEndTime = Date.now() + SESSION_DURATION;
        localStorage.setItem('sessionEndTime', sessionEndTime);
    } else {
        sessionEndTime = parseInt(sessionEndTime, 10);
    }

    const interval = setInterval(function() {
        const remaining = Math.max(0, sessionEndTime - Date.now());
        
        if (remaining <= 0) {
            clearInterval(interval);
            timeDisplay.textContent = "00:00";
            timerDiv.style.backgroundColor = "#ef4444"; // red warning
            window.location.href = "/logout";
        } else {
            const totalSeconds = Math.floor(remaining / 1000);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            timeDisplay.textContent = 
                (minutes < 10 ? "0" : "") + minutes + ":" + 
                (seconds < 10 ? "0" : "") + seconds;
                
            // Turn orange if less than 60 seconds
            if (totalSeconds < 60) {
                timerDiv.style.backgroundColor = "#d97706";
            }
        }
    }, 1000);
});
