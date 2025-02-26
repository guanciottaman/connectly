function accept(username, userId) {
    // Send the user's ID to the Flask backend
    fetch('/set-user-id', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: userId })  // Send the user ID
    })
    .then(response => response.json())
    .then(data => {
        // If successful, redirect to the chat page for that user
        if (data.success) {
            window.location.href = `/chat/${username}`;
        } else {
            // Handle any errors
            console.error(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}


function reject() {
    sessionStorage.removeItem("chat_with_user_id");  // Or use localStorage if needed

    // Redirect the user back to the profile or home page
    window.location.href = '/chat';  // Redirecting to home page or profile page
}