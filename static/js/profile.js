let currentField = "";  // This will store the field that is being edited


function editField(field) {
    let textElement = document.getElementById(field);
    let currentValue = textElement.innerText;

    // Set the current field being edited
    currentField = field;

    // Show the save button when editing
    document.getElementById("edit-controls").style.display = "block";

    // Replace text with input or textarea field based on the field
    if (field !== "bio") {
        textElement.innerHTML = `<input type="text" id="${field}-input" value="${currentValue}">`;
    } else {
        textElement.innerHTML = `<textarea id="${field}-input" rows="4" cols="50">${currentValue}</textarea>`;
    }

    // Focus on the input/textarea field
    document.getElementById(field + '-input').focus();
}

function saveField() {
    let inputElement;

    // If the field is 'bio', handle it as a textarea
    if (currentField === 'bio') {
        inputElement = document.getElementById(currentField + '-input');
    } else {
        inputElement = document.getElementById(currentField + "-input");
    }

    let newValue = inputElement.value;
    // Show the spinner immediately when the request starts
    document.getElementById("loading-spinner").style.display = "block";

    // Disable the input field while the request is processing
    inputElement.disabled = true;

    // Send to backend via fetch
    fetch("/edit_profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field: currentField, value: newValue })
    })
    .then(response => response.json())
    .then(data => {
        // Hide the spinner once the response is received
        document.getElementById("loading-spinner").style.display = "none";

        // Re-enable the input field after the request is done
        inputElement.disabled = false;

        if (data.success) {
            // Update text with new value
            document.getElementById(currentField).innerHTML = newValue;

            // If the updated field is "username", also update the <h2> element
            if (currentField === 'username') {
                document.querySelector("h2").innerText = newValue;
            }
        } else {
            alert("Error updating profile.");
        }
    })
    .catch(error => {
        // Hide the spinner in case of error
        document.getElementById("loading-spinner").style.display = "none";
        
        // Re-enable the input field in case of error
        inputElement.disabled = false;

        alert("Error processing your request.");
    });

    // Hide the save button after saving
    document.getElementById("edit-controls").style.display = "none";
};
