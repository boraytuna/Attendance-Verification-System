document.addEventListener("DOMContentLoaded", function () {
    const allFrames = document.getElementsByTagName("section");
    const table = document.getElementById("tableBody");
    const userAgreement = document.getElementById("userAgreement");
    const privacyPolicy = document.getElementById("privacyPolicy");
    const btnAllowLocation = document.getElementById("btnAllowLocation");
    const btnSubmitEndLocation = document.getElementById("btnSubmitEndLocation");
    const emailNotice = document.getElementById("emailSentNotice");
    const resendBtn = document.getElementById("resendEmailBtn");
    const timerSpan = document.getElementById("resendTimer");
    let sendingInProgress = false;
    let locationCaptured = false;

    let classSelectInstance;
    let profSelectInstance;

    let frameState = sessionStorage.getItem("frameState");
    let emailVerified = sessionStorage.getItem("emailVerified") === "true";

    // 🧠 Use localStorage fallback if sessionStorage is gone
    if (!frameState) {
        const payload = localStorage.getItem("student_checkin_payload");
        if (payload) {
            try {
                const parsed = JSON.parse(payload);
                if (parsed && parsed.email && parsed.scannedEventID) {
                    frameState = "3"; // Assume Frame 4: student already checked in and should wait to submit end location
                    sessionStorage.setItem("frameState", "3");
                    sessionStorage.setItem("cachedStudent", JSON.stringify({
                        email: parsed.email,
                        lastName: parsed.lastName,
                        scannedEventID: parsed.scannedEventID
                    }));
                }
            } catch (e) {
                console.warn("Could not parse localStorage payload for frameState fallback.");
            }
        }
    }

    // 👇 Enhanced frame logic — supports Frame 2 restoration
    let resendStarted = sessionStorage.getItem("resendTimerStarted") === "true";
    let resendStartTime = parseInt(sessionStorage.getItem("resendStartTime") || "0", 10);
    let elapsed = Math.floor((Date.now() - resendStartTime) / 1000);
    let remaining = 180 - elapsed;

    if (frameState === "1" && resendStarted && remaining > 0) {
        showFrame(1); // Frame 2
        emailNotice.style.display = "block";
        startResendCountdown(remaining);
    } else if (frameState === "2" && emailVerified) {
        showFrame(2); // Frame 3
    } else if (frameState === "4") {
        showFrame(4); // Frame 5
    } else if (frameState === "5") {
        showFrame(5); // Frame 6
    } else {
        showFrame(0); // Frame 1
    }


    let cachedStudent = JSON.parse(sessionStorage.getItem("cachedStudent")) || {
        email: '',
        lastName: '',
        scannedEventID: ''
    };

    // Check if event end time has passed
    let eventEndTime = new Date(document.body.getAttribute("data-event-end")); // ISO string format
    let now = new Date();

    if (eventEndTime && now > eventEndTime) {
        // Event has ended
        showFrame(5); // Frame 6 index (0-based)
        return;
    }

    if (!cachedStudent.scannedEventID) {
        const pathParts = window.location.pathname.split('/');
        if (pathParts.includes("student_checkin")) {
            cachedStudent.scannedEventID = pathParts[pathParts.indexOf("student_checkin") + 1];
            sessionStorage.setItem("cachedStudent", JSON.stringify(cachedStudent));
        }
    }

    // 🔁 Restore cached student data if user returns later (like hours later)
    const savedPayload = localStorage.getItem("student_checkin_payload");
    if (savedPayload) {
        try {
            const parsed = JSON.parse(savedPayload);
            if (parsed && parsed.email && parsed.lastName && parsed.scannedEventID) {
                cachedStudent.email = parsed.email;
                cachedStudent.lastName = parsed.lastName;
                cachedStudent.scannedEventID = parsed.scannedEventID;
            }
        } catch (e) {
            console.warn("Failed to parse saved check-in payload", e);
        }
    }

    function showFrame(frameIndex) {
        for (let i = 0; i < allFrames.length; i++) {
            allFrames[i].style.display = i === frameIndex ? "block" : "none";
        }

        restoreFormData(); // ✅ Always restore
    }

    function saveFormData() {
        let rows = document.querySelectorAll("#tableBody tr:not(#tableHeader)");
        let courseTable = [];

        rows.forEach(row => {
            let cells = row.querySelectorAll("td");
            if (cells.length >= 2) {
                courseTable.push({
                    className: cells[0].innerText.trim(),
                    professorName: cells[1].innerText.trim()
                });
            }
        });

        const formData = {
            firstName: document.getElementById("firstName").value,
            lastName: document.getElementById("lastName").value,
            email: document.getElementById("studentEmail").value,
            courseTable: courseTable // ⬅️ Add this
        };

        sessionStorage.setItem("studentFormData", JSON.stringify(formData));
    }

    function restoreFormData() {
        const formData = JSON.parse(sessionStorage.getItem("studentFormData"));
        if (!formData) return;

        document.getElementById("firstName").value = formData.firstName || "";
        document.getElementById("lastName").value = formData.lastName || "";
        document.getElementById("studentEmail").value = formData.email || "";

        if (Array.isArray(formData.courseTable)) {
            formData.courseTable.forEach(entry => {
                let newRow = document.createElement("tr");
                newRow.setAttribute("id", "tableRow");

                let courseCell = document.createElement("td");
                courseCell.innerText = entry.className;
                newRow.appendChild(courseCell);

                let profCell = document.createElement("td");
                profCell.innerText = entry.professorName;
                newRow.appendChild(profCell);

                let deleteCell = document.createElement("td");
                let icon = document.createElement("i");
                icon.classList.add("fa-solid", "fa-trash-can");
                icon.setAttribute("style", "cursor: pointer; color: red;");
                deleteCell.appendChild(icon);
                newRow.appendChild(deleteCell);

                icon.addEventListener("click", function () {
                    newRow.remove();
                    saveFormData();
                });

                table.appendChild(newRow);
            });
        }
    }

    function startResendCountdown(seconds) {
        resendBtn.disabled = true;
        let remaining = seconds;

        // 🔐 Save the start time and flag for refresh persistence
        sessionStorage.setItem("resendTimerStarted", "true");
        sessionStorage.setItem("resendStartTime", Date.now().toString());

        const interval = setInterval(() => {
            const mins = Math.floor(remaining / 60);
            const secs = remaining % 60;
            timerSpan.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
            remaining--;

            if (remaining < 0) {
                clearInterval(interval);
                resendBtn.disabled = false;
                timerSpan.textContent = "Ready to resend.";
            }
        }, 1000);
    }

    function handleGeolocationError(error) {
        let message = "";
        switch (error.code) {
            case 1:
                message = "Location permission was denied. Please allow access to use this feature.";
                break;
            case 2:
                message = "Location unavailable. Make sure you're connected to the internet or try stepping outside.";
                break;
            case 3:
                message = "Location request timed out. Please try again.";
                break;
            default:
                message = "An unknown error occurred while retrieving location.";
        }
        showError(`📍 Location Error (${error.code}): ${message}`);
    }

    function updateAllowLocationButton() {
        btnAllowLocation.disabled = !(userAgreement.checked && privacyPolicy.checked);
    }

    function getLocationAndSubmit() {
        const classInput = document.getElementById("className").value.trim();
        const profInput = document.getElementById("professorName").value.trim();

        // 🛑 Warn user about unsubmitted class/professor
        if ((classInput || profInput) && classInput !== "" && profInput !== "") {
            const confirmSkip = confirm("You have a class and professor selected that haven't been added to the table. Do you want to continue without adding them?");
            if (!confirmSkip) return;
        }

        // 🛑 Ensure at least one course is added to the table
        const rows = document.querySelectorAll("#tableBody tr:not(#tableHeader)");
        if (rows.length === 0) {
            alert("You must add at least one course with a professor before submitting.");
            return;
        }

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function (position) {
                    let lat = position.coords.latitude;
                    let lon = position.coords.longitude;
                    let capturedStudentLocation = `${lat},${lon}`;
                    locationCaptured = true;

                    cachedStudent.firstName = document.getElementById("firstName").value.trim();
                    cachedStudent.lastName = document.getElementById("lastName").value.trim();
                    cachedStudent.email = document.getElementById("studentEmail").value.trim();

                    if (!cachedStudent.firstName || !cachedStudent.lastName || !cachedStudent.email) {
                        alert("Missing student information. Please return to the start.");
                        showFrame(0);
                        return;
                    }

                    submitStudentCheckin(capturedStudentLocation);
                },
                error => {
                    console.error("📍 Geolocation error:", error);
                    handleGeolocationError(error);
                },
                {enableHighAccuracy: true, timeout: 15000, maximumAge: 0}
            );
        } else {
            alert("Geolocation not supported by your browser.");
        }
    }

    function submitStudentCheckin(capturedStudentLocation) {
        let rows = document.querySelectorAll("#tableBody tr:not(#tableHeader)");
        let courseData = [];

        rows.forEach(row => {
            let cells = row.querySelectorAll("td");
            if (cells.length >= 2) {
                courseData.push({
                    className: cells[0].innerText.trim(),
                    professorName: cells[1].innerText.trim()
                });
            }
        });

        const checkinTime = new Date().toISOString();

        let formData = {
            firstName: cachedStudent.firstName,
            lastName: cachedStudent.lastName,
            email: cachedStudent.email,
            scannedEventID: cachedStudent.scannedEventID,
            studentLocation: capturedStudentLocation,
            checkinTime: checkinTime, // ✅ add timestamp
            deviceId: getDeviceId(),
            courses: courseData
        };

        fetch('/submit_student_checkin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        })
            .then(async response => {
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(errorText);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === "success") {
                    alert("Check-in successful!");

                    localStorage.setItem("student_checkin_payload", JSON.stringify(formData));
                    sessionStorage.setItem("cachedStudent", JSON.stringify(cachedStudent));
                    sessionStorage.setItem("frameState", "3");
                    document.getElementById("errorMessage").style.display = "none";
                    showFrame(3); // Frame 4: wait for event to end
                } else {
                    showError(data.message || "Check-in failed. Please try again.");
                }
            })
            .catch(async error => {
                try {
                    const parsed = JSON.parse(error.message);
                    if (parsed.message && parsed.message.toLowerCase().includes("device has already been used")) {
                        showErrorWithRestart("🚫 This device has already been used to check in. Please contact the event organizer.");
                    } else {
                        showError(parsed.message || "Unknown error occurred.");
                    }
                } catch (parseErr) {
                    console.error("🚨 Fetch failed:", error);
                    showError("Network or server error:\n" + error.message);
                }
            });
    }

    function getDeviceId() {
        let deviceId = localStorage.getItem("device_id");
        if (!deviceId) {
            deviceId = crypto.randomUUID();
            localStorage.setItem("device_id", deviceId);
        }
        return deviceId;
    }

    function submitEndLocation(capturedEndLocation) {
        const {email, lastName, scannedEventID} = cachedStudent;

        const endPayload = {
            email,
            lastName,
            scannedEventID,
            endLocation: capturedEndLocation,
            endTime: new Date().toISOString(), // ✅ add timestamp
            deviceId: getDeviceId()             // ✅ include for consistency
        };

        fetch('/submit_end_location', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(endPayload)
        })
            .then(async response => {
                if (!response.ok) throw new Error(await response.text());
                return response.json();
            })
            .then(data => {
                if (data.status === "success") {
                    alert("End location submitted successfully!");
                    sessionStorage.setItem("frameState", "4");
                    showFrame(4); // Frame 5: confirmation
                } else {
                    showError(data.message || "Submission failed.");
                }
            })
            .catch(error => {
                showError("Error submitting end location:\n" + error.message);
            });
    }

    function showError(message) {
        const errorBox = document.getElementById("errorMessage");
        errorBox.innerText = message;
        errorBox.style.display = "block";

        // ✅ Fix here: move timeout inside this function to access `errorBox`
        setTimeout(() => {
            errorBox.style.display = "none";
        }, 6000);
    }

    function createNewTableRow() {
        try {
            const classVal = classSelectInstance?.getValue().trim();
            const professorVal = profSelectInstance?.getValue().trim();

            if (!classVal || !professorVal) return false;

            let newTableRow = document.createElement("tr");
            newTableRow.setAttribute("id", "tableRow");

            let newCourseCell = document.createElement("td");
            newCourseCell.innerText = classVal;
            newTableRow.appendChild(newCourseCell);

            let newProfessorCell = document.createElement("td");
            newProfessorCell.innerText = professorVal;
            newTableRow.appendChild(newProfessorCell);

            let newDeleteCell = document.createElement("td");
            let icon = document.createElement("i");
            icon.classList.add("fa-solid", "fa-trash-can");
            icon.setAttribute("style", "cursor: pointer; color: red;");
            newDeleteCell.appendChild(icon);
            newTableRow.appendChild(newDeleteCell);

            icon.addEventListener("click", function () {
                newTableRow.remove();
                saveFormData();
            });

            document.getElementById("tableBody").appendChild(newTableRow);
            saveFormData();

            // ✅ Clear both selects and update button
            classSelectInstance.clear();
            profSelectInstance.clear();
            toggleAddRowButton();

            return true;
        } catch (err) {
            console.error("❌ createNewTableRow failed:", err);
            return false;
        }
    }

    function toggleAddRowButton() {
        const classVal = document.getElementById("className").value.trim();
        const profVal = document.getElementById("professorName").value.trim();
        document.getElementById("addRowToTable").disabled = !(classVal && profVal);
    }

    ["className", "professorName"].forEach(id => {
        const el = document.getElementById(id);
        el.addEventListener("change", toggleAddRowButton);
        el.addEventListener("input", toggleAddRowButton); // add this line ✅
    });

    function showErrorWithRestart(message) {
        const errorBox = document.getElementById("errorMessage");
        errorBox.innerHTML = `${message}<br><button id='restartBtn' style='margin-top:10px;background:white;color:#e63946;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;'>Return to Start</button>`;
        errorBox.style.display = "block";

        document.getElementById("restartBtn").addEventListener("click", () => {
            sessionStorage.clear();
            cachedStudent = {email: '', lastName: '', scannedEventID: ''};
            showFrame(0);
        });
    }

    ["firstName", "lastName", "studentEmail"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener("input", saveFormData);
        }
    });

    // Element id for submit buttons on frame 1 and 2
    document.getElementById("btnSubmitFrame1").addEventListener("click", function (e) {
        e.preventDefault();

        if (sendingInProgress) return;
        sendingInProgress = true;

        const firstName = document.getElementById("firstName").value.trim();
        const lastName = document.getElementById("lastName").value.trim();
        const email = document.getElementById("studentEmail").value.trim();

        if (!firstName || !lastName || !email) {
            alert("Please fill out your first name, last name, and student email before continuing.");
            sendingInProgress = false;
            return;
        }

        const button = document.getElementById("btnSubmitFrame1");
        button.disabled = true;
        button.innerText = "Sending...";

        cachedStudent.email = email;
        cachedStudent.lastName = lastName;
        cachedStudent.scannedEventID = window.location.pathname.split('/')[2];

        if (emailNotice && resendBtn && timerSpan) {
            fetch('/verify_email', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email: email})
            })
                .then(response => response.text())
                .then(() => {
                    sessionStorage.setItem("resendTimerStarted", "true");
                    sessionStorage.setItem("resendStartTime", Date.now().toString());
                    showFrame(1);
                    sessionStorage.setItem("frameState", 1);

                    resendBtn.addEventListener("click", () => {
                        fetch("/resend_verification_email", {
                            method: "POST",
                            headers: {"Content-Type": "application/json"},
                            body: JSON.stringify({email: document.getElementById("studentEmail").value})
                        })
                            .then(res => {
                                if (res.ok) {
                                    startResendCountdown(180);
                                    alert("Verification email resent!");
                                } else {
                                    alert("Failed to resend email.");
                                }
                            });
                    });

                    emailNotice.style.display = "block";
                    startResendCountdown(180);
                })
                .catch(error => {
                    console.error('Error:', error);
                })
                .finally(() => {
                    sendingInProgress = false;
                    button.disabled = false;
                    button.innerText = "Verify Email";
                });
        } else {
            console.error("Missing email notice elements in DOM.");
            sendingInProgress = false;
        }
    });
    document.getElementById("btnSubmitFrame2").addEventListener("click", function (e) {
        e.preventDefault();

        const code = document.getElementById("securityCode").value.trim();

        if (!code) {
            alert("Please enter the security code before continuing.");
            return;
        }

        fetch('/verify_code', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code: code})
        })
            .then(response => response.json())
            .then(data => {
                if (data.message === 'Code verified') {
                    alert(data.message);
                    sessionStorage.setItem("emailVerified", "true");
                    sessionStorage.setItem("frameState", "2"); // ✅ Save it correctly as Frame 3
                    showFrame(2); // still shows Frame 3
                } else {
                    alert(data.error);
                    sessionStorage.removeItem("studentFormData");

                    document.getElementById("studentEmail").value = "";
                    document.getElementById("lastName").value = "";
                    document.getElementById("firstName").value = "";
                    document.getElementById("securityCode").value = "";

                    cachedStudent.email = '';
                    cachedStudent.lastName = '';
                    cachedStudent.scannedEventID = '';

                    showFrame(0);
                }
            })
            .catch(error => console.error('Error:', error));
    });
    document.getElementById("addRowToTable").addEventListener("click", function (event) {
        event.preventDefault();
        createNewTableRow();
    });
    document.getElementById("className").addEventListener("change", toggleAddRowButton);
    document.getElementById("professorName").addEventListener("change", toggleAddRowButton);

    userAgreement.addEventListener("change", updateAllowLocationButton);
    privacyPolicy.addEventListener("change", updateAllowLocationButton);

    btnAllowLocation.addEventListener("click", getLocationAndSubmit);
    btnSubmitEndLocation.addEventListener("click", function () {
        if (!cachedStudent.email || !cachedStudent.lastName || !cachedStudent.scannedEventID) {
            // try restoring from form
            cachedStudent.email = document.getElementById("studentEmail").value.trim();
            cachedStudent.lastName = document.getElementById("lastName").value.trim();
            cachedStudent.scannedEventID = window.location.pathname.split('/')[2];
        }

        if (!cachedStudent.email || !cachedStudent.lastName || !cachedStudent.scannedEventID) {
            alert("Missing student data. Please refresh.");
            return;
        }

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function (position) {
                    const capturedEndLocation = `${position.coords.latitude},${position.coords.longitude}`;
                    submitEndLocation(capturedEndLocation); // ✅ use helper
                },
                error => {
                    console.error("📍 End location error:", error);
                    handleGeolocationError(error);
                },
                {enableHighAccuracy: true, timeout: 15000, maximumAge: 0}
            );
        } else {
            alert("Geolocation not supported by this browser.");
        }
    });

    document.getElementById("securityCode").addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            document.getElementById("btnSubmitFrame2").click();
        }
    });

    // Load courses
    fetch('/search_courses?query=')
        .then(res => res.json())
        .then(data => {
            classSelectInstance = new TomSelect("#className", {
                placeholder: "Select or type a class name...",
                create: true,
                maxItems: 1,
                valueField: "name",
                labelField: "name",
                searchField: "name",
                options: data.map(name => ({name: name.name || name})),
            });
        });

// Load professors
    fetch('/search_professors?query=')
        .then(res => res.json())
        .then(data => {
            profSelectInstance = new TomSelect("#professorName", {
                placeholder: "Select or type a professor name...",
                create: true,
                maxItems: 1,
                valueField: "name",
                labelField: "name",
                searchField: "name",
                options: data.map(name => ({name: name.name || name})),
            });
        });
});
