document.addEventListener("DOMContentLoaded", function () {
    let currentFrameIndex = 0;
    const allFrames = document.getElementsByTagName("section");
    const table = document.getElementById("tableBody");
    const userAgreement = document.getElementById("userAgreement");
    const privacyPolicy = document.getElementById("privacyPolicy");
    const btnAllowLocation = document.getElementById("btnAllowLocation");
    const btnSubmitEndLocation = document.getElementById("btnSubmitEndLocation");
    let locationCaptured = false;

    let frameState = sessionStorage.getItem("frameState");
    let emailVerified = sessionStorage.getItem("emailVerified") === "true";

    // Logic for deciding which frame to show
    if (frameState === "4") {
        showFrame(3); // Frame 4 is index 3
    } else if (frameState === "3" && emailVerified) {
        showFrame(2); // Frame 3 is index 2
    } else {
        showFrame(0); // Everything else redirects to Frame 1
    }


    let cachedStudent = JSON.parse(sessionStorage.getItem("cachedStudent")) || {
        email: '',
        lastName: '',
        scannedEventID: ''
    };

    if (!cachedStudent.scannedEventID) {
        const pathParts = window.location.pathname.split('/');
        if (pathParts.includes("student_checkin")) {
            cachedStudent.scannedEventID = pathParts[pathParts.indexOf("student_checkin") + 1];
            sessionStorage.setItem("cachedStudent", JSON.stringify(cachedStudent));
        }
    }


    window.addEventListener("beforeunload", () => {
        if (currentFrameIndex >= 2) {
            sessionStorage.setItem("currentFrame", currentFrameIndex.toString());
        }
    });

    function showFrame(frameIndex) {
        for (let i = 0; i < allFrames.length; i++) {
            allFrames[i].style.display = i === frameIndex ? "block" : "none";
        }
        currentFrameIndex = frameIndex;

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

        let formData = {
            firstName: cachedStudent.firstName,
            lastName: cachedStudent.lastName,
            email: cachedStudent.email,
            scannedEventID: cachedStudent.scannedEventID,
            studentLocation: capturedStudentLocation,
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
                    sessionStorage.setItem("cachedStudent", JSON.stringify(cachedStudent));
                    document.getElementById("errorMessage").style.display = "none";
                    showFrame(3);
                    sessionStorage.setItem("frameState", 3);
                } else {
                    const reason = data.message || "Check-in failed. Please try again.";
                    showError(reason);
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
                    showFrame(4); // maybe final frame
                    sessionStorage.setItem("frameState", 4);
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
            const classInput = document.getElementById("className");
            const professorInput = document.getElementById("professorName");

            const classVal = classInput.value.trim();
            const professorVal = professorInput.value.trim();

            if (!classVal || !professorVal) return false;

            let newTableRow = document.createElement("tr");
            table.appendChild(newTableRow);
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

            // ✅ Clear inputs after adding
            classInput.value = "";
            professorInput.value = "";
            document.getElementById("addRowToTable").disabled = true;

            // ✅ Also clear TomSelect values
            if (window.TomSelect) {
                if (TomSelect.instances["className"]) TomSelect.instances["className"].clear();
                if (TomSelect.instances["professorName"]) TomSelect.instances["professorName"].clear();
            }

            saveFormData(); // ✅ Save after addition
            return true;
        } catch (error) {
            console.error("❌ Error adding row:", error);
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

        const firstName = document.getElementById("firstName").value.trim();
        const lastName = document.getElementById("lastName").value.trim();
        const email = document.getElementById("studentEmail").value.trim();

        if (!firstName || !lastName || !email) {
            alert("Please fill out your first name, last name, and student email before continuing.");
            return;
        }

        cachedStudent.email = email;
        cachedStudent.lastName = lastName;
        cachedStudent.scannedEventID = window.location.pathname.split('/')[2];

        fetch('/verify_email', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: email})
        })
            .then(response => response.text())
            .catch(error => console.error('Error:', error));

        showFrame(1);
        sessionStorage.setItem("frameState", 1);
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
                    sessionStorage.setItem("frameState", "3"); // Frame 3 = index 2
                    showFrame(2); // Frame 3
                } else {
                    alert(data.error);
                    sessionStorage.removeItem("studentFormData");
                    sessionStorage.removeItem("currentFrame");

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
        event.preventDefault(); //prevent default form submission
        if (createNewTableRow()) {
            //clear input fields after adding to table
            document.getElementById("className").value = "";
            document.getElementById("professorName").value = "";
            //disable add button
            document.getElementById("addRowToTable").disabled = true;
        }
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

    // Load courses
    fetch('/search_courses?query=')
        .then(res => res.json())
        .then(data => {
            new TomSelect("#className", {
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
            new TomSelect("#professorName", {
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

