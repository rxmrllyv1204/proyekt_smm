window.API_URL = (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.protocol === 'file:' ||
    /^(\d{1,3}\.){3}\d{1,3}$/.test(window.location.hostname)
) ? `http://${window.location.hostname === 'localhost' || window.location.protocol === 'file:' ? '127.0.0.1' : window.location.hostname}:8000` : window.location.origin;

console.log("API_URL set to:", window.API_URL);

// Auth Helpers
const saveToken = (token) => localStorage.setItem('auth_token', token);
const getToken = () => localStorage.getItem('auth_token');
const logout = () => {
    localStorage.removeItem('auth_token');
    window.location.href = 'login.html';
};

window.apiSendVerifCode = async (email) => {
    const response = await fetch(`${window.API_URL}/register/send-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Kod yuborishda xatolik");
    }
    return response.json();
};

window.apiVerifyRegister = async (username, email, password, code) => {
    console.log("Attempting verification for:", email);
    try {
        const response = await fetch(`${window.API_URL}/register/verify-code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, code })
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Tasdiqlashda xatolik");
        }
        return response.json();
    } catch (e) {
        console.error("Fetch error in apiVerifyRegister:", e);
        throw e;
    }
};

window.apiLogin = async (username, password) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const response = await fetch(`${window.API_URL}/token`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params
    });

    if (!response.ok) {
        let errorMsg = "Login failed";
        try {
            const error = await response.json();
            errorMsg = error.detail || errorMsg;
        } catch (e) {
            console.error("Non-JSON error response", e);
        }
        throw new Error(errorMsg);
    }
    const data = await response.json();
    saveToken(data.access_token);
    return data;
};

window.fetchUsers = async () => {
    const response = await fetch(`${window.API_URL}/admin/users`);
    if (!response.ok) throw new Error("Failed to fetch users");
    return response.json();
};

window.fetchOrders = async () => {
    const response = await fetch(`${window.API_URL}/admin/orders`);
    if (!response.ok) throw new Error("Failed to fetch orders");
    return response.json();
};

window.fetchMe = async () => {
    const token = getToken();
    if (!token) throw new Error("Not logged in");

    const response = await fetch(`${window.API_URL}/me`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    if (!response.ok) {
        logout();
        throw new Error("Session expired");
    }
    return response.json();
};

window.updateUserBalance = async (userId, amount) => {
    console.log(`Attempting to update balance for user ${userId} by ${amount}`);
    const response = await fetch(`${window.API_URL}/admin/users/${userId}/balance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount })
    });
    if (!response.ok) {
        const error = await response.json();
        console.error("Balance update failed:", error);
        throw new Error(error.detail || "Balance update failed");
    }
    console.log(`Balance updated for user ${userId}`);
    return response.json();
};

window.patchOrder = async (orderId, status) => {
    console.log(`Attempting to patch order ${orderId} with status ${status}`);
    const response = await fetch(`${window.API_URL}/admin/orders/${orderId}?status=${encodeURIComponent(status)}`, {
        method: 'PATCH'
    });
    if (!response.ok) {
        const error = await response.json();
        console.error("Order update failed:", error);
        throw new Error(error.detail || "Order update failed");
    }
    console.log(`Order ${orderId} updated successfully`);
    return response.json();
};

window.apiUpdateOrder = async (orderId, orderData) => {
    const response = await fetch(`${window.API_URL}/admin/orders/${orderId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData)
    });
    if (!response.ok) throw new Error("Order update failed");
    return response.json();
};

window.apiPlaceOrder = async (orderData) => {
    const token = getToken();
    if (!token) throw new Error("Tizimga kirmagansiz");

    const response = await fetch(`${window.API_URL}/orders`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(orderData)
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Buyurtma yuborishda xatolik");
    }
    return response.json();
};

window.apiDeleteOrder = async (orderId) => {
    console.log(`Attempting to delete order ${orderId}`);
    const response = await fetch(`${window.API_URL}/admin/orders/${orderId}`, {
        method: 'DELETE'
    });
    if (!response.ok) {
        const error = await response.json();
        console.error("Order deletion failed:", error);
        throw new Error(error.detail || "Order deletion failed");
    }
    console.log(`Order ${orderId} deleted successfully`);
    return response.json();
};

window.getApiSettings = async () => {
    const response = await fetch(`${window.API_URL}/admin/api-settings`);
    if (!response.ok) throw new Error("API settings fetch failed");
    return response.json();
};

window.saveApiSettings = async (settings) => {
    const response = await fetch(`${window.API_URL}/admin/api-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    });
    if (!response.ok) throw new Error("API settings save failed");
    return response.json();
};

window.fetchServices = async () => {
    const response = await fetch(`${window.API_URL}/services`);
    if (!response.ok) throw new Error("Xizmatlarni yuklashda xatolik");
    return response.json();
};

window.fetchMyOrders = async () => {
    const token = getToken();
    if (!token) throw new Error("Tizimga kirmagansiz");

    const response = await fetch(`${window.API_URL}/users/me/orders`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    if (!response.ok) throw new Error("Buyurtmalarni yuklashda xatolik");
    return response.json();
};

window.saveService = async (serviceData) => {
    const response = await fetch(`${window.API_URL}/admin/services`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(serviceData)
    });
    if (!response.ok) {
        const errData = await response.json();
        throw new Error("Xizmatni saqlashda xatolik: " + (errData.detail || response.status));
    }
    return response.json();
};

window.deleteService = async (serviceId) => {
    const response = await fetch(`${window.API_URL}/admin/services/${serviceId}`, {
        method: 'DELETE'
    });
    if (!response.ok) {
        throw new Error("Xizmatni o'chirishda xatolik: " + response.status);
    }
    return response.json();
};

// Payment System Functions
window.apiSubmitTopup = async (amount, method, receiptFile = null) => {
    const token = getToken();
    if (!token) throw new Error("Tizimga kirmagansiz");

    const formData = new FormData();
    formData.append('amount', amount);
    formData.append('method', method);
    if (receiptFile) {
        formData.append('receipt', receiptFile);
    }

    const url = `${window.API_URL}/payments/request`;
    console.log(`Fetching: ${url}`);
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: "Noma'lum xatolik (Server error)" }));
            console.error("Topup submission failed:", err);
            throw new Error(err.detail || "To'lov so'rovida xatolik");
        }
        return response.json();
    } catch (e) {
        console.error("Fetch error in apiSubmitTopup:", e);
        throw e;
    }
};

window.apiFetchPaymentRequests = async () => {
    const response = await fetch(`${window.API_URL}/admin/payment-requests`);
    if (!response.ok) throw new Error("To'lov so'rovlarini yuklashda xatolik");
    return response.json();
};

window.apiUpdatePaymentRequestStatus = async (reqId, status) => {
    const response = await fetch(`${window.API_URL}/admin/payment-requests/${reqId}/status?status=${encodeURIComponent(status)}`, {
        method: 'POST'
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Holatni yangilashda xatolik");
    }
    return response.json();
};

window.apiFetchPaymentSettings = async () => {
    const response = await fetch(`${window.API_URL}/admin/payment-settings`);
    if (!response.ok) throw new Error("To'lov sozlamalarini yuklashda xatolik");
    return response.json();
};

window.apiUpdatePaymentSettings = async (method, settings) => {
    const response = await fetch(`${window.API_URL}/admin/payment-settings/${method}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    });
    if (!response.ok) throw new Error("To'lov sozlamalarini saqlashda xatolik");
    return response.json();
};

window.apiRegenerateKey = async () => {
    const token = getToken();
    if (!token) throw new Error("Tizimga kirmagansiz");

    const response = await fetch(`${window.API_URL}/users/me/api-key`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    if (!response.ok) throw new Error("API kalitni yangilashda xatolik");
    return response.json();
};

window.apiCreateTicket = async (formData) => {
    const token = getToken();
    const response = await fetch(`${window.API_URL}/support/tickets`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
    });
    if (!response.ok) throw new Error("Murojaatni yuborishda xatolik");
    return response.json();
};

window.apiFetchMyTickets = async () => {
    const token = getToken();
    const response = await fetch(`${window.API_URL}/support/my-tickets`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.json();
};

window.apiFetchAllTickets = async () => {
    const response = await fetch(`${window.API_URL}/admin/support/tickets`);
    return response.json();
};

window.apiReplyToTicket = async (id, reply) => {
    const response = await fetch(`${window.API_URL}/admin/support/tickets/${id}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reply })
    });
    if (!response.ok) throw new Error("Javob yuborishda xatolik");
    return response.json();
};


// Admin Session persistent helper
window.setAdminAuth = (status) => sessionStorage.setItem('admin_auth', status);
window.getAdminAuth = () => sessionStorage.getItem('admin_auth');

// Theme Controller
const initTheme = () => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Select all potential toggle buttons and icons
    const toggles = document.querySelectorAll('#themeToggle, #themeToggleAuth, .theme-toggle-btn');
    const icons = document.querySelectorAll('#themeIcon, .theme-icon');

    const updateUI = (theme) => {
        icons.forEach(icon => {
            icon.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
        });
        if (window.lucide) {
            lucide.createIcons();
        }
    };

    updateUI(savedTheme);

    toggles.forEach(btn => {
        btn.onclick = (e) => {
            e.preventDefault();
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateUI(newTheme);
        };
    });
};

// Order Price Calculation Logic
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    const serviceSelect = document.getElementById('service');
    if (serviceSelect) {
        const quantityInput = document.getElementById('quantity');
        const totalPriceDisplay = document.getElementById('totalPrice');
        const orderForm = document.getElementById('orderForm');

        const updatePrice = () => {
            const selectedOption = serviceSelect.options[serviceSelect.selectedIndex].text;
            // Matches any currency symbol followed by numbers or just the numbers before /1000
            const priceMatch = selectedOption.match(/(\d+\.?\d*)\/1000/);

            if (priceMatch && quantityInput.value) {
                const pricePerThousand = parseFloat(priceMatch[1]);
                const quantity = parseInt(quantityInput.value);
                const total = (quantity / 1000) * pricePerThousand;
                totalPriceDisplay.textContent = `${total.toLocaleString()} so'm`;
            } else {
                totalPriceDisplay.textContent = `0 so'm`;
            }
        };

        serviceSelect.addEventListener('change', updatePrice);
        quantityInput.addEventListener('input', updatePrice);

        if (orderForm) {
            orderForm.addEventListener('submit', (e) => {
                e.preventDefault();
                alert(`Rahmat! Buyurtmangiz qabul qilindi.`);
                orderForm.reset();
                updatePrice();
            });
        }
    }
});

// End of Admin Management Logic
