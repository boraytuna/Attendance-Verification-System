// document.addEventListener("DOMContentLoaded", function () {
//     ///// Navigation Between Frames /////
//     const allFrames = document.getElementsByTagName("section");
//
//     function getCurrentFrame() {
//         for (let i = 0; i < allFrames.length; i++) {
//             if (allFrames[i].style.display !== "none") {
//                 return i;
//             }
//         }
//     }
//
//     function showFrame(frameIndex) {
//         for (let i = 0; i < allFrames.length; i++) {
//             allFrames[i].style.display = i === frameIndex ? "block" : "none";
//         }
//     }
//
//     showFrame(getCurrentFrame());
//
//     // Frame navigation buttons
//     document.getElementById("btnSubmitFrame1").addEventListener("click", function () {
//         showFrame(1);
//     });
//
//     document.getElementById("btnSubmitFrame2").addEventListener("click", function () {
//         showFrame(2);
//     });
//
//     ///// Frame 1 - Verify Email Button Action /////
//     document.getElementById("btnSubmitFrame1").addEventListener("click", function (e) {
//         e.preventDefault();
//
//         let email = document.getElementById("studentEmail").value;
//         fetch('/verify_email', {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({ email: email })
//         })
//         .then(response => response.text())
//         .catch(error => console.error('Error:', error));
//     });
//
//     ///// Frame 2 - Verify Code Button Action /////
//     document.getElementById("btnSubmitFrame2").addEventListener("click", function (e) {
//         e.preventDefault();
//
//         let code = document.getElementById("securityCode").value;
//         fetch('/verify_code', {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({ code: code })
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.message === 'Code verified') {
//                 alert(data.message);
//                 showFrame(2);
//             } else {
//                 alert(data.error);
//             }
//         })
//         .catch(error => console.error('Error:', error));
//     });
//
//     ///// Frame 3 - Professor and Course Suggestion Autopopulation /////
//     function fetchSuggestions(inputId, apiEndpoint, datalistId) {
//         document.getElementById(inputId).addEventListener('input', function () {
//             let searchQuery = this.value;
//             if (searchQuery.length > 1) {
//                 fetch(apiEndpoint + '?query=' + searchQuery)
//                     .then(response => response.json())
//                     .then(data => {
//                         let datalist = document.getElementById(datalistId);
//                         datalist.innerHTML = "";
//                         data.forEach(item => {
//                             let option = document.createElement('option');
//                             option.value = item;
//                             datalist.appendChild(option);
//                         });
//                     });
//             }
//         });
//     }
//
//     fetchSuggestions('className', '/search_courses', 'courseSuggestions');
//     fetchSuggestions('professorName', '/search_professors', 'professorSuggestions');
//
//     ///// Frame 3 - Location and Agreement Check /////
//     const userAgreement = document.getElementById("userAgreement");
//     const privacyPolicy = document.getElementById("privacyPolicy");
//     const btnAllowLocation = document.getElementById("btnAllowLocation");
//     const btnFinish = document.getElementById("btnFinish"); // Finish button
//     const locationDisplay = document.getElementById("locationDisplay");
//     const studentLocation = document.getElementById("studentLocation");
//
//     let locationCaptured = false;
//     let formSubmitted = false;
//
//     function updateAllowLocationButton() {
//         // Enable "Allow Access" only if both checkboxes are checked
//         btnAllowLocation.disabled = !(userAgreement.checked && privacyPolicy.checked);
//     }
//
//     function updateAllowFinishButton() {
//         // Enable "Finish" button only if checkboxes are checked, location is captured, and form is submitted
//         btnFinish.disabled = !(userAgreement.checked && privacyPolicy.checked && locationCaptured && formSubmitted);
//     }
//
//     userAgreement.addEventListener("change", updateAllowLocationButton);
//     privacyPolicy.addEventListener("change", updateAllowLocationButton);
//
//     function getLocationAndSubmit() {
//         if (navigator.geolocation) {
//             navigator.geolocation.getCurrentPosition(
//                 function (position) {
//                     let lat = position.coords.latitude;
//                     let lon = position.coords.longitude;
//
//                     // Store location in hidden field for submission
//                     //studentLocation.value = `${lat},${lon}`;
//
//                     let capturedStudentLocation = `${lat},${lon}`;
//                     locationCaptured = true;
//
//                     // Submit form only after location is retrieved
//                     submitStudentCheckin(capturedStudentLocation);
//                 },
//                 function (error) {
//                     console.error("Geolocation error:", error);
//                     //alert("Location access denied or unavailable.");
//                     alert(error.code, error.message);
//                 },
//                 { enableHighAccuracy: true }
//             );
//         } else {
//             alert("Geolocation not supported by your browser.");
//         }
//     }
//
//     btnAllowLocation.addEventListener("click", getLocationAndSubmit);
//
//     function handleGeolocationError(error) {
//         let message = "";
//
//         switch (error.code) {
//             case 1:
//                 message = "Location permission was denied. Please allow access to use this feature.";
//                 break;
//             case 2:
//                 message = "Location unavailable. Make sure you're connected to the internet or try stepping outside.";
//                 break;
//             case 3:
//                 message = "Location request timed out. Please try again.";
//                 break;
//             default:
//                 message = "An unknown error occurred while retrieving location.";
//         }
//
//         alert(`Error (${error.code}): ${message}`);
//     }
//
//     ///// Frame 3 - Submit Form & Enable Finish Button /////
//     const url = window.location.pathname;
//
//     function submitStudentCheckin(capturedStudentLocation) {
//         let formData = {
//             firstName: document.getElementById("firstName").value,
//             lastName: document.getElementById("lastName").value,
//             email: document.getElementById("studentEmail").value,
//             classForExtraCredit: document.getElementById("className").value,
//             professorForExtraCredit: document.getElementById("professorName").value,
//             scannedEventID: url.split('/')[2],
//             studentLocation: capturedStudentLocation,
//         };
//
//         fetch('/submit_student_checkin', {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify(formData)
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.status === "success") {
//                 alert("Check-in successful!");
//                 formSubmitted = true;
//                 updateAllowFinishButton(); // Enable Finish button after submission
//             } else {
//                 alert("Check-in failed. Please try again.");
//             }
//         })
//         .catch(error => console.error("Error:", error));
//     }
//
//     ///// Frame 3 - Finish Button Loads Frame 4 /////
//     btnFinish.addEventListener("click", function () {
//         if (!btnFinish.disabled) {
//             showFrame(3);
//         }
//     });
//
//     ///// Frame 4 - Capture and Submit End Location /////
//     const btnSubmitEndLocation = document.getElementById("btnSubmitEndLocation");
//
//     btnSubmitEndLocation.addEventListener("click", function () {
//         if (navigator.geolocation) {
//             navigator.geolocation.getCurrentPosition(
//                 function (position) {
//                     let endLat = position.coords.latitude;
//                     let endLon = position.coords.longitude;
//                     let capturedEndLocation = `${endLat},${endLon}`;
//                     locationCaptured = true;
//
//                     let endPayload = {
//                         email: document.getElementById("studentEmail").value,
//                         scannedEventID: url.split('/')[2],
//                         endLocation: capturedEndLocation,
//                     };
//
//                     fetch('/submit_end_location', {
//                         method: 'POST',
//                         headers: { 'Content-Type': 'application/json' },
//                         body: JSON.stringify(endPayload)
//                     })
//                     .then(response => response.json())
//                     .then(data => {
//                         if (data.status === "success") {
//                             alert("End location successfully submitted!");
//                             btnSubmitEndLocation.disabled = true;
//                         } else {
//                             alert("Something went wrong submitting your final location.");
//                         }
//                     })
//                     .catch(error => console.error("Error submitting end location:", error));
//                 },
//                 function (error) {
//                     console.error("Geolocation error:", error);
//                     alert("Could not retrieve location. Please try again.");
//                 },
//                 { enableHighAccuracy: true }
//             );
//         } else {
//             alert("Geolocation is not supported by your browser.");
//         }
//     });
// });
document.addEventListener("DOMContentLoaded", function () {
    ///// Navigation Between Frames /////
    const allFrames = document.getElementsByTagName("section");

    function getCurrentFrame() {
        for (let i = 0; i < allFrames.length; i++) {
            if (allFrames[i].style.display !== "none") {
                return i;
            }
        }
    }

    function showFrame(frameIndex) {
        for (let i = 0; i < allFrames.length; i++) {
            allFrames[i].style.display = i === frameIndex ? "block" : "none";
        }
    }

    showFrame(getCurrentFrame());

    ///// Geolocation Error Handler /////
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

        alert(`Error (${error.code}): ${message}`);
    }

    // Frame navigation buttons
    document.getElementById("btnSubmitFrame1").addEventListener("click", function () {
        showFrame(1);
    });

    document.getElementById("btnSubmitFrame2").addEventListener("click", function () {
        showFrame(2);
    });

    ///// Frame 1 - Verify Email Button Action /////
    document.getElementById("btnSubmitFrame1").addEventListener("click", function (e) {
        e.preventDefault();

        let email = document.getElementById("studentEmail").value;
        fetch('/verify_email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        })
        .then(response => response.text())
        .catch(error => console.error('Error:', error));
    });

    ///// Frame 2 - Verify Code Button Action /////
    document.getElementById("btnSubmitFrame2").addEventListener("click", function (e) {
        e.preventDefault();

        let code = document.getElementById("securityCode").value;
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
            }
        })
        .catch(error => console.error('Error:', error));
    });

    ///// Frame 3 - Professor and Course Suggestion Autopopulation /////
    function fetchSuggestions(inputId, apiEndpoint, datalistId) {
        document.getElementById(inputId).addEventListener('input', function () {
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

    ///// Frame 3 - Location and Agreement Check /////
    const userAgreement = document.getElementById("userAgreement");
    const privacyPolicy = document.getElementById("privacyPolicy");
    const btnAllowLocation = document.getElementById("btnAllowLocation");
    const btnFinish = document.getElementById("btnFinish");
    const locationDisplay = document.getElementById("locationDisplay");
    const studentLocation = document.getElementById("studentLocation");

    let locationCaptured = false;
    let formSubmitted = false;

    function updateAllowLocationButton() {
        btnAllowLocation.disabled = !(userAgreement.checked && privacyPolicy.checked);
    }

    function updateAllowFinishButton() {
        btnFinish.disabled = !(userAgreement.checked && privacyPolicy.checked && locationCaptured && formSubmitted);
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
                handleGeolocationError,
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
        } else {
            alert("Geolocation not supported by your browser.");
        }
    }

    btnAllowLocation.addEventListener("click", getLocationAndSubmit);

    const url = window.location.pathname;

    function submitStudentCheckin(capturedStudentLocation) {
        let formData = {
            firstName: document.getElementById("firstName").value,
            lastName: document.getElementById("lastName").value,
            email: document.getElementById("studentEmail").value,
            classForExtraCredit: document.getElementById("className").value,
            professorForExtraCredit: document.getElementById("professorName").value,
            scannedEventID: url.split('/')[2],
            studentLocation: capturedStudentLocation,
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
                formSubmitted = true;
                updateAllowFinishButton();
            } else {
                alert("Check-in failed. Please try again.");
            }
        })
        .catch(error => console.error("Error:", error));
    }

    btnFinish.addEventListener("click", function () {
        if (!btnFinish.disabled) {
            showFrame(3);
        }
    });
    ///// Frame 4 - Capture and Submit End Location /////
    const btnSubmitEndLocation = document.getElementById("btnSubmitEndLocation");

    btnSubmitEndLocation.addEventListener("click", function () {
        const emailField = document.getElementById("studentEmail");
        const lastNameField = document.getElementById("lastName");
        const email = emailField ? emailField.value : null;
        const lastName = lastNameField ? lastNameField.value : null;
        const scannedEventID = url.split('/')[2];

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
                        email: email,
                        lastName: lastName,
                        scannedEventID: scannedEventID,
                        endLocation: capturedEndLocation,
                    };

                    console.log("Sending end location payload:", endPayload);

                    fetch('/submit_end_location', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(endPayload)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === "success") {
                            alert("End location successfully submitted!");
                            btnSubmitEndLocation.disabled = true;
                        } else {
                            console.error("Backend error:", data);
                            alert("Something went wrong submitting your final location.");
                        }
                    })
                    .catch(error => {
                        console.error("Fetch error:", error);
                        alert("Network error while submitting location.");
                    });
                },
                handleGeolocationError,
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
        } else {
            alert("Geolocation is not supported by your browser.");
        }
    });
});
