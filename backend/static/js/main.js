document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");
    const taskForm = document.getElementById("task-form");
    const taskList = document.getElementById("task-list"); // Assuming you have a div or ul with id "task-list"
    const reminderList = document.getElementById("reminder-list");
    const addReminderForm = document.getElementById("add-reminder-form");

    // Login Form Handler
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = loginForm.email.value.trim();
            const password = loginForm.password.value.trim();

            // Validate fields
            if (!email || !password) {
                showAlert("Please fill out all fields.", "error");
                return;
            }

            try {
                const response = await fetch("/login", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ email, password })
                });

                const result = await response.json();
                if (result.success) {
                    showAlert("Login successful!", "success");
                    window.location.href = "/dashboard"; // Redirect to the dashboard
                } else {
                    showAlert("Login failed: " + result.message, "error");
                }
            } catch (error) {
                console.error("Login error:", error);
                showAlert("Something went wrong. Please try again.", "error");
            }
        });
    }

    // Signup Form Handler
    if (signupForm) {
        signupForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = signupForm.username.value.trim();
            const email = signupForm.email.value.trim();
            const password = signupForm.password.value.trim();

            // Validate fields
            if (!username || !email || !password) {
                showAlert("Please fill out all fields.", "error");
                return;
            }

            // Basic Email Format Validation
            const emailPattern = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
            if (!emailPattern.test(email)) {
                showAlert("Please enter a valid email address.", "error");
                return;
            }

            try {
                const response = await fetch("/signup", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ username, email, password })
                });

                const result = await response.json();
                if (result.success) {
                    showAlert("Signup successful! Redirecting to login...", "success");
                    setTimeout(() => window.location.href = "/login", 2000); // Redirect after 2 seconds
                } else {
                    showAlert("Signup failed: " + result.message, "error");
                }
            } catch (error) {
                console.error("Signup error:", error);
                showAlert("Something went wrong. Please try again.", "error");
            }
        });
    }

    // Task Form Handler (for adding or updating tasks)
    if (taskForm) {
        taskForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const taskName = taskForm.task_name.value.trim();
            const taskDescription = taskForm.task_description.value.trim();
            const dueDate = taskForm.due_date.value.trim();

            // Validate fields
            if (!taskName || !dueDate) {
                showAlert("Please fill out all fields.", "error");
                return;
            }

            try {
                const taskId = taskForm.task_id.value; // Get task ID if editing existing task
                const url = taskId ? `/tasks/edit/${taskId}` : "/tasks/add"; // Different endpoint for edit/add
                const method = taskId ? "POST" : "POST"; // Both are POST but with different URLs
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ task_name: taskName, task_description: taskDescription, due_date: dueDate })
                });

                const result = await response.json();
                if (result.success) {
                    showAlert(taskId ? "Task updated successfully!" : "Task added successfully!", "success");
                    window.location.reload(); // Reload the page after success
                } else {
                    showAlert("Task operation failed: " + result.message, "error");
                }
            } catch (error) {
                console.error("Task operation error:", error);
                showAlert("Something went wrong. Please try again.", "error");
            }
        });
    }

    // Task Deletion Handler (assuming there's a button or link to delete tasks)
    if (taskList) {
        taskList.addEventListener("click", async (e) => {
            if (e.target && e.target.matches(".delete-task")) {
                const taskId = e.target.getAttribute("data-task-id");

                try {
                    const response = await fetch(`/tasks/delete/${taskId}`, {
                        method: "POST",
                    });

                    const result = await response.json();
                    if (result.success) {
                        showAlert("Task deleted successfully!", "success");
                        e.target.closest(".task-item").remove(); // Remove the task item from the UI
                    } else {
                        showAlert("Task deletion failed: " + result.message, "error");
                    }
                } catch (error) {
                    console.error("Task deletion error:", error);
                    showAlert("Something went wrong. Please try again.", "error");
                }
            }
        });
    }

    // Fetch and display reminders
    async function fetchReminders() {
        try {
            const response = await fetch("/reminders");
            const reminders = await response.json();
            renderReminders(reminders);
        } catch (error) {
            console.error("Error fetching reminders:", error);
        }
    }

    // Render reminders
    function renderReminders(reminders) {
        reminderList.innerHTML = "";

        if (reminders.length === 0) {
            reminderList.innerHTML = `<li class="text-center py-4 text-gray-500">No reminders. Add some to get started!</li>`;
            return;
        }

        reminders.forEach((reminder) => {
            const item = document.createElement("li");
            item.className = "flex items-center p-3 bg-white rounded-md shadow-sm border border-gray-200";
            item.innerHTML = `
                <div class="flex-grow">
                    <h3 class="font-semibold text-gray-800">${reminder.title}</h3>
                    <p class="text-sm text-gray-600">${reminder.description}</p>
                    <p class="text-xs text-gray-500">Due: ${new Date(reminder.due_date).toLocaleString()}</p>
                </div>
                <button onclick="deleteReminder('${reminder._id}')" class="text-red-600 hover:text-red-800">Delete</button>
            `;
            reminderList.appendChild(item);
        });
    }

    // Show Add Reminder Form
    window.showAddReminderForm = function () {
        addReminderForm.classList.remove("hidden");
    };

    // Hide Add Reminder Form
    window.hideAddReminderForm = function () {
        addReminderForm.classList.add("hidden");
    };

    // Add Reminder
    window.addReminder = async function () {
        const title = document.getElementById("reminder-title").value.trim();
        const description = document.getElementById("reminder-description").value.trim();
        const dueDate = document.getElementById("reminder-due-date").value.trim();

        if (!title || !dueDate) {
            alert("Title and due date are required.");
            return;
        }

        try {
            const response = await fetch("/reminders/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, description, due_date: dueDate }),
            });

            const result = await response.json();
            if (result.success) {
                alert("Reminder added successfully!");
                fetchReminders();
                hideAddReminderForm();
            } else {
                alert("Failed to add reminder.");
            }
        } catch (error) {
            console.error("Error adding reminder:", error);
        }
    };

    // Delete Reminder
    window.deleteReminder = async function (reminderId) {
        if (!confirm("Are you sure you want to delete this reminder?")) return;

        try {
            const response = await fetch(`/reminders/delete/${reminderId}`, { method: "POST" });
            const result = await response.json();
            if (result.success) {
                alert("Reminder deleted successfully!");
                fetchReminders();
            } else {
                alert("Failed to delete reminder.");
            }
        } catch (error) {
            console.error("Error deleting reminder:", error);
        }
    };

    // Fetch reminders on page load
    fetchReminders();

    // Helper function to show alerts (could be replaced with Toast notifications)
    function showAlert(message, type) {
        const alertBox = document.createElement("div");
        alertBox.classList.add("alert");
        alertBox.classList.add(type === "success" ? "alert-success" : "alert-error");
        alertBox.textContent = message;

        document.body.appendChild(alertBox);
        setTimeout(() => {
            alertBox.remove();
        }, 4000);
    }

    function toggleTheme() {
        const html = document.documentElement;
        const isDark = html.classList.toggle('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }

    // Apply the saved theme on page load
    document.addEventListener('DOMContentLoaded', () => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    });
});
