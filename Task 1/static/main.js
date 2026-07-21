// --- IMAGE LIGHTBOX ---
// Opens the image in a fullscreen view
function viewImage(imageSrc) {
    const portal = document.getElementById("lightboxPortal");
    const enlargedImage = document.getElementById("lightboxImage");
    if (portal && enlargedImage) {
        enlargedImage.src = imageSrc;
        portal.style.display = "flex";
    }
}

// Closes the fullscreen view
function closeImage() {
    const portal = document.getElementById("lightboxPortal");
    if (portal) {
        portal.style.display = "none";
    }
}

// --- FORUM COMPOSER ---
// Toggles the visibility of the post creation form
function toggleComposer() {
    const formContent = document.getElementById("composerFormContent");
    if (formContent) {
        formContent.style.display =
            formContent.style.display === "block" ? "none" : "block";
    }
}

// Shows a preview when a user selects an image for a new post
function handleImageQuickSelect(event) {
    const file = event.target.files[0];
    const container = document.getElementById("previewBox");
    const img = document.getElementById("previewImg");
    const formContent = document.getElementById("composerFormContent");

    if (file && file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = function (e) {
            if (img) img.src = e.target.result;
            if (container) container.style.display = "block";
            if (container) container.classList.remove("hidden");
            if (container) container.classList.add("visible");
            if (formContent) formContent.style.display = "block";
        };
        reader.readAsDataURL(file);
    }
}

// Removes the image from the new post composer
function clearComposerImage() {
    const container = document.getElementById("previewBox");
    const img = document.getElementById("previewImg");
    const fileInput = document.getElementById("image_trigger");
    if (img) img.src = "";
    if (container) container.classList.add("hidden");
    if (container) container.classList.remove("visible");
    if (container) container.style.display = "none";
    if (fileInput) fileInput.value = "";
}

// Resets and closes the new post composer
function closeComposerReset() {
    clearComposerImage();
    const formContent = document.getElementById("composerFormContent");
    const subjectInput = document.getElementById("subject");
    const messageInput = document.getElementById("message_text");

    if (subjectInput) subjectInput.value = "";
    if (messageInput) messageInput.value = "";
    if (formContent) formContent.style.display = "none";
}

// --- EDIT POST PAGE ---
// Shows a preview when the user selects a new image to replace the old one
function handleEditImageSelect(event) {
    const file = event.target.files[0];
    const container = document.getElementById("previewBox");
    const img = document.getElementById("previewImg");
    const deleteFlag = document.getElementById("delete_image");

    if (file && file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = function (e) {
            if (img) img.src = e.target.result;
            if (container) {
                container.classList.remove("hidden");
                container.classList.add("visible");
            }
            if (deleteFlag) deleteFlag.value = "false";
        };
        reader.readAsDataURL(file);
    }
}

// Removes the image from an existing post and tells the server to delete it
function clearEditFormImage() {
    const container = document.getElementById("previewBox");
    const img = document.getElementById("previewImg");
    const deleteFlag = document.getElementById("delete_image");
    const fileInput = document.getElementById("image");
    if (img) img.src = "";
    if (container) {
        container.classList.remove("visible");
        container.classList.add("hidden");
    }
    if (deleteFlag) deleteFlag.value = "true";
    if (fileInput) fileInput.value = "";
}

// --- FORM UTILITIES ---
// Prevents users from clicking "Submit" twice while the page is loading
document.addEventListener("submit", (event) => {
    const submitBtn = event.target.querySelector(
        'button[type="submit"], .btn[type="submit"]',
    );

    if (submitBtn) {
        // Show a loading message based on the button's purpose
        const buttonText = submitBtn.innerText.toLowerCase();
        if (buttonText.includes("update")) submitBtn.innerText = "Updating...";
        else if (buttonText.includes("change"))
            submitBtn.innerText = "Changing...";
        else submitBtn.innerText = "Submitting...";

        submitBtn.style.opacity = "0.6";
        submitBtn.style.cursor = "not-allowed";

        // Disable the button shortly after starting the submit process
        setTimeout(() => {
            submitBtn.disabled = true;
        }, 1);
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeImage();
    }
});

function enableUsernameEdit() {
    const input = document.getElementById("new_username");
    const editButton = document.getElementById("editUsernameBtn");
    const changeButton = document.getElementById("changeUsernameBtn");
    const cancelButton = document.getElementById("cancelUsernameBtn");

    input.disabled = false;
    input.focus();
    input.select();

    editButton.classList.add("hidden");
    changeButton.classList.remove("hidden");
    cancelButton.classList.remove("hidden");
}

function cancelUsernameEdit() {
    const input = document.getElementById("new_username");
    const editButton = document.getElementById("editUsernameBtn");
    const changeButton = document.getElementById("changeUsernameBtn");
    const cancelButton = document.getElementById("cancelUsernameBtn");

    input.value = input.defaultValue;
    input.disabled = true;

    editButton.classList.remove("hidden");
    changeButton.classList.add("hidden");
    cancelButton.classList.add("hidden");
}

function enablePasswordEdit() {
    const oldPassword = document.getElementById("old_password");
    const newPassword = document.getElementById("new_password");
    const editButton = document.getElementById("editPasswordBtn");
    const changeButton = document.getElementById("changePasswordBtn");
    const cancelButton = document.getElementById("cancelPasswordBtn");

    oldPassword.disabled = false;
    newPassword.disabled = false;
    oldPassword.focus();

    editButton.classList.add("hidden");
    changeButton.classList.remove("hidden");
    cancelButton.classList.remove("hidden");
}

function cancelPasswordEdit() {
    const oldPassword = document.getElementById("old_password");
    const newPassword = document.getElementById("new_password");
    const editButton = document.getElementById("editPasswordBtn");
    const changeButton = document.getElementById("changePasswordBtn");
    const cancelButton = document.getElementById("cancelPasswordBtn");

    oldPassword.value = "";
    newPassword.value = "";

    oldPassword.disabled = true;
    newPassword.disabled = true;

    editButton.classList.remove("hidden");
    changeButton.classList.add("hidden");
    cancelButton.classList.add("hidden");
}
