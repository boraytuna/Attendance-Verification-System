document.addEventListener("DOMContentLoaded", function () {
    let currentFrameIndex = 0;

    window.addEventListener("beforeunload", () => {
        if (currentFrameIndex >= 2) {
            sessionStorage.setItem("currentFrame", currentFrameIndex.toString());
        }
    });

    let cachedStudent = {
        email: '',
        lastName: '',
        scannedEventID: ''
    };

    const allFrames = document.getElementsByTagName("section");

    function showFrame(frameIndex) {
        for (let i = 0; i < allFrames.length; i++) {
            allFrames[i].style.display = i === frameIndex ? "block" : "none";
        }
        currentFrameIndex = frameIndex;
    }

    const savedFrame = parseInt(sessionStorage.getItem("currentFrame"));
    if (!isNaN(savedFrame)) {
        showFrame(savedFrame);
        restoreFormData();
    } else {
        showFrame(0);
    }

    ["firstName", "lastName", "studentEmail", "className", "professorName"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener("input", saveFormData);
        }
    });

    function saveFormData() {
        const formData = {
            firstName: document.getElementById("firstName").value,
            lastName: document.getElementById("lastName").value,
            email: document.getElementById("studentEmail").value,
            className: document.getElementById("className")?.value || "",
            professorName: document.getElementById("professorName")?.value || ""
        };
        sessionStorage.setItem("studentFormData", JSON.stringify(formData));
    }

    function restoreFormData() {
        const formData = JSON.parse(sessionStorage.getItem("studentFormData"));
        if (formData) {
            document.getElementById("firstName").value = formData.firstName || "";
            document.getElementById("lastName").value = formData.lastName || "";
            document.getElementById("studentEmail").value = formData.email || "";
            if (document.getElementById("className")) {
                document.getElementById("className").value = formData.className || "";
            }
            if (document.getElementById("professorName")) {
                document.getElementById("professorName").value = formData.professorName || "";
            }
        }
    }

    const restoredCache = JSON.parse(sessionStorage.getItem("cachedStudent"));
    if (restoredCache) {
        cachedStudent = restoredCache;
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        })
        .then(response => response.text())
        .catch(error => console.error('Error:', error));

        showFrame(1);
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message === 'Code verified') {
                alert(data.message);
                showFrame(2);
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

    function fetchSuggestions(inputId, apiEndpoint, datalistId) {
        const el = document.getElementById(inputId);
        if (!el) return;
        el.addEventListener('input', function () {
            let searchQuery = this.value;
            if (searchQuery.length > 1) {
                fetch(apiEndpoint + '?query=' + searchQuery)
                    .then(response => response.json())
                    .then(data => {
                        let datalist = document.getElementById(datalistId);
                        datalist.innerHTML = "";
                        data.forEach(item => {
                            let option = document.createElement('option');
                            option.value = item;
                            datalist.appendChild(option);
                        });
                    });
            }
        });
    }

    fetchSuggestions('className', '/search_courses', 'courseSuggestions');
    fetchSuggestions('professorName', '/search_professors', 'professorSuggestions');

    const userAgreement = document.getElementById("userAgreement");
    const privacyPolicy = document.getElementById("privacyPolicy");
    const btnAllowLocation = document.getElementById("btnAllowLocation");

    let locationCaptured = false;

    function updateAllowLocationButton() {
        btnAllowLocation.disabled = !(userAgreement.checked && privacyPolicy.checked);
    }

    userAgreement.addEventListener("change", updateAllowLocationButton);
    privacyPolicy.addEventListener("change", updateAllowLocationButton);

    function getLocationAndSubmit() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function (position) {
                    let lat = position.coords.latitude;
                    let lon = position.coords.longitude;
                    let capturedStudentLocation = `${lat},${lon}`;
                    locationCaptured = true;
                    submitStudentCheckin(capturedStudentLocation);
                },
                error => {
                    console.error("📍 Geolocation error:", error);
                    handleGeolocationError(error);
                },
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
            );
        } else {
            alert("Geolocation not supported by your browser.");
        }
    }

    btnAllowLocation.addEventListener("click", getLocationAndSubmit);

    function submitStudentCheckin(capturedStudentLocation) {
        let formData = {
            firstName: document.getElementById("firstName").value,
            lastName: cachedStudent.lastName,
            email: cachedStudent.email,
            classForExtraCredit: document.getElementById("className").value,
            professorForExtraCredit: document.getElementById("professorName").value,
            scannedEventID: cachedStudent.scannedEventID,
            studentLocation: capturedStudentLocation,
            deviceId: getDeviceId()
        };

        fetch('/submit_student_checkin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                alert("Check-in successful!");
                sessionStorage.setItem("cachedStudent", JSON.stringify(cachedStudent));
                showFrame(3); // Keep session alive until end location is done
            } else {
                const reason = data.message || "Check-in failed. Please try again.";
                alert(`❌ Check-in failed:\n${reason}`);
            }
        })
        .catch(error => {
            console.error("Check-in error:", error);
            alert("Network or server error. Try again later.");
        });
    }

    const btnSubmitEndLocation = document.getElementById("btnSubmitEndLocation");

    btnSubmitEndLocation.addEventListener("click", function () {
        if (!cachedStudent.email || !cachedStudent.lastName || !cachedStudent.scannedEventID) {
            cachedStudent.email = document.getElementById("studentEmail").value.trim();
            cachedStudent.lastName = document.getElementById("lastName").value.trim();
            cachedStudent.scannedEventID = window.location.pathname.split('/')[2];
        }

        const { email, lastName, scannedEventID } = cachedStudent;

        if (!email || !lastName || !scannedEventID) {
            alert("Missing student email, last name, or event ID. Please reload the page and try again.");
            return;
        }

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function (position) {
                    let endLat = position.coords.latitude;
                    let endLon = position.coords.longitude;
                    let capturedEndLocation = `${endLat},${endLon}`;

                    let endPayload = {
                        email,
                        lastName,
                        scannedEventID,
                        endLocation: capturedEndLocation,
                    };

                    fetch('/submit_end_location', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(endPayload)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === "success") {
                            alert("End location successfully submitted!");
                            sessionStorage.removeItem("currentFrame");
                            sessionStorage.removeItem("studentFormData");
                            sessionStorage.removeItem("cachedStudent");
                            showFrame(4);
                        } else {
                            alert("Something went wrong submitting your final location.");
                        }
                    })
                    .catch(error => {
                        console.error("Fetch error:", error);
                        alert("Network error while submitting location.");
                    });
                },
                error => {
                    console.error("📍 Geolocation error:", error);
                    handleGeolocationError(error);
                },
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
            );
        } else {
            alert("Geolocation is not supported by your browser.");
        }
    });

    function getDeviceId() {
        let deviceId = localStorage.getItem("device_id");
        if (!deviceId) {
            deviceId = crypto.randomUUID();
            localStorage.setItem("device_id", deviceId);
        }
        return deviceId;
    }

    function showError(message) {
        const errorBox = document.getElementById("errorMessage");
        errorBox.innerText = message;
        errorBox.style.display = "block";
    }

    setTimeout(() => {
        errorBox.style.display = "none";
    }, 6000);

    function createNewTableRow() {
        try {
            //create new table row, append to table
            let newTableRow = document.createElement("tr");
            table.appendChild(newTableRow);
            newTableRow.setAttribute("id", "tableRow");

            //create Course Name cell in new row, append to new row
            let newCourseCell = document.createElement("td");
            newTableRow.append(newCourseCell);
            //set the inner text of the cell to the value of the className input field
            newCourseCell.innerText = document.getElementById("className").value;

            //create Professor Name cell in new row, append to new row
            let newProfessorCell = document.createElement("td");
            newTableRow.appendChild(newProfessorCell);
            //set the inner text of the cell to the value of the professorName input field
            newProfessorCell.innerText = document.getElementById("professorName").value;

            //delete icon
            let newDeleteCell = document.createElement("td");
            let icon = document.createElement("i");
            icon.classList.add("fa-solid", "fa-trash-can");
            icon.setAttribute("style", "cursor: pointer; color: red;");
            newDeleteCell.appendChild(icon);
            newTableRow.appendChild(newDeleteCell);

            //remove row when delete icon clicked
            icon.addEventListener("click", function () {
                newTableRow.remove();
            });

            return true;
        } catch (error) {
            return false;
        }
    }

    //disable add button if either class or professor input is empty
    function toggleAddRowButton() {
        if (document.getElementById("className").value != "" && document.getElementById("professorName").value != "") {
            document.getElementById("addRowToTable").disabled = false;
        } else {
            document.getElementById("addRowToTable").disabled = true;
        }
    }

    document.getElementById("className").addEventListener("change", toggleAddRowButton);
    document.getElementById("professorName").addEventListener("change", toggleAddRowButton);

    const table = document.getElementById("tableBody");
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
});