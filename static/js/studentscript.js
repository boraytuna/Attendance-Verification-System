document.addEventListener("DOMContentLoaded", function () {
    ///// Navigation Between Frames /////
    const allFrames = document.getElementsByTagName("section");
    
    //Get the index of the current visible frame
    function getCurrentFrame() {
        for (let i = 0; i < allFrames.length; i++) {
            if (allFrames[i].style.display !== "none") {
                return i;
            }
        }
    }

    //Show the frame with the given index
    function showFrame(frameIndex) {
        for (let i = 0; i < allFrames.length; i++) {
            if (i != frameIndex) {
                allFrames[i].style.display = "none";
            } else {
                allFrames[i].style.display = "block";
            }
        }
    }

    showFrame(getCurrentFrame());

    //button to move from frame 1 to frame 2
    const btnSubmitFrame1 = document.getElementById("btnSubmitFrame1");
    btnSubmitFrame1.addEventListener("click", function () {
        showFrame(1);
    });

    //button to move from frame 2 to frame 3
    /* const btnSubmitFrame2 = document.getElementById("btnSubmitFrame2");
    btnSubmitFrame2.addEventListener("click", function () {
        showFrame(2);
    }); */

    //button to move from frame 3 to frame 4
    const btnSubmitFrame3 = document.getElementById("btnSubmitFrame3");
    btnSubmitFrame3.addEventListener("click", function () {
        showFrame(3);
    });

    ///// Frame 1 - Verify Email Button Action /////
    document.getElementById("btnSubmitFrame1").addEventListener("click", function(e) {
        e.preventDefault(); //prevent form submission and page refresh

        let email = document.getElementById("studentEmail").value;
        fetch('/verify_email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email
            })
        })
        .then(response => response.text()) //response from server
        .catch(error => console.error('Error:', error)) //error handling
    });

    ///// Frame 2 - Verify Code Button Action /////
    document.getElementById("btnSubmitFrame2").addEventListener("click", function(e) {
        e.preventDefault(); //prevent form submission and page refresh

        let code = document.getElementById("securityCode").value;
        fetch('/verify_code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code
            })
        })
        .then(response => response.json()) //response from server
        .then(data => {
            if (data.message == 'Code verified') {
                alert(data.message); //display the success message returned from verify_code()
                showFrame(2); //move from frame 2 to frame 3
            } else {
                alert(data.error); //display the error message returned from verify_code()
            }
        })
        .catch(error => console.error('Error:', error)) //error handling
    });

    ///// Frame 3 - Professor and Course Suggestion Autopopulation /////

    //fetch suggestions from server database
    function fetchSuggestions(inputId, apiEndpoint, datalistId) {
        document.getElementById(inputId).addEventListener('input', function() {
            let searchQuery = this.value;
            if (searchQuery.length > 1) { //query strings with length > 1
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

    ///// Push Form Data To Server /////
    const url = window.location.pathname;

    //todo - ensure fields are valid and requirements met before submitting (e.g. agreed to privacy policies)
    btnSubmitFrame3.addEventListener("click", function () {
        let studentID = "temporary string"; //todo - get student ID from form or remove from schema
        let firstName = document.getElementById("firstName").value;
        let lastName = document.getElementById("lastName").value;
        let email = document.getElementById("studentEmail").value;
        let classForExtraCredit = document.getElementById("className").value;
        let professorForExtraCredit = document.getElementById("professorName").value;
        let scannedEventID = url.split('/')[2];
        let studentLocation = "temporary string"; //todo - get location from device

        fetch('/submit_student_checkin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                studentID: studentID,
                firstName: firstName,
                lastName: lastName,
                email: email,
                classForExtraCredit: classForExtraCredit,
                professorForExtraCredit: professorForExtraCredit,
                scannedEventID: scannedEventID,
                studentLocation: studentLocation
            })
        })
        .then(response => response.json())
    });
});