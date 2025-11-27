module.exports = [
"[externals]/react/jsx-dev-runtime [external] (react/jsx-dev-runtime, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("react/jsx-dev-runtime", () => require("react/jsx-dev-runtime"));

module.exports = mod;
}),
"[externals]/react [external] (react, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("react", () => require("react"));

module.exports = mod;
}),
"[project]/lib/api.js [ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

// Frontend API Client for CampusNexus
// Communicates with Django backend
__turbopack_context__.s([
    "apiDelete",
    ()=>apiDelete,
    "apiGet",
    ()=>apiGet,
    "apiPatch",
    ()=>apiPatch,
    "apiPost",
    ()=>apiPost,
    "apiPostFormData",
    ()=>apiPostFormData,
    "apiPut",
    ()=>apiPut,
    "clearToken",
    ()=>clearToken,
    "default",
    ()=>__TURBOPACK__default__export__,
    "setToken",
    ()=>setToken
]);
const API_BASE_URL = ("TURBOPACK compile-time value", "http://localhost:8000") || 'http://localhost:8000';
class ApiClient {
    constructor(){
        this.baseURL = API_BASE_URL;
        this.token = null;
        // Try to load token from localStorage if in browser
        if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
        ;
    }
    setToken(token) {
        this.token = token;
        if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
        ;
    }
    clearToken() {
        this.token = null;
        if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
        ;
    }
    getHeaders(customHeaders = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...customHeaders
        };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    }
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: this.getHeaders(options.headers)
        };
        try {
            const response = await fetch(url, config);
            // Handle different response types
            const contentType = response.headers.get('content-type');
            let data;
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }
            if (!response.ok) {
                throw new Error(data.message || data.error || `HTTP error! status: ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
    async get(endpoint) {
        return this.request(endpoint, {
            method: 'GET'
        });
    }
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }
    async patch(endpoint, data) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
    // Convenience method for form data (file uploads)
    async postFormData(endpoint, formData) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        // Don't set Content-Type for FormData - browser will set it with boundary
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: formData
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || data.error || `HTTP error! status: ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
}
// Export singleton instance
const apiClient = new ApiClient();
const __TURBOPACK__default__export__ = apiClient;
const { get: apiGet, post: apiPost, put: apiPut, patch: apiPatch, delete: apiDelete, setToken, clearToken, postFormData: apiPostFormData } = apiClient;
}),
"[project]/context/AuthContext.js [ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

// original: N/A - new file for authentication context
// Auth Context for CampusNexus Frontend
// Manages user authentication state across the application
__turbopack_context__.s([
    "AuthProvider",
    ()=>AuthProvider,
    "useAuth",
    ()=>useAuth
]);
var __TURBOPACK__imported__module__$5b$externals$5d2f$react$2f$jsx$2d$dev$2d$runtime__$5b$external$5d$__$28$react$2f$jsx$2d$dev$2d$runtime$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/react/jsx-dev-runtime [external] (react/jsx-dev-runtime, cjs)");
var __TURBOPACK__imported__module__$5b$externals$5d2f$react__$5b$external$5d$__$28$react$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/react [external] (react, cjs)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$js__$5b$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.js [ssr] (ecmascript)");
;
;
;
const AuthContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$externals$5d2f$react__$5b$external$5d$__$28$react$2c$__cjs$29$__["createContext"])();
function useAuth() {
    const context = (0, __TURBOPACK__imported__module__$5b$externals$5d2f$react__$5b$external$5d$__$28$react$2c$__cjs$29$__["useContext"])(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
}
function AuthProvider({ children }) {
    const [user, setUser] = (0, __TURBOPACK__imported__module__$5b$externals$5d2f$react__$5b$external$5d$__$28$react$2c$__cjs$29$__["useState"])(null);
    const [loading, setLoading] = (0, __TURBOPACK__imported__module__$5b$externals$5d2f$react__$5b$external$5d$__$28$react$2c$__cjs$29$__["useState"])(true);
    // Check for existing session on mount
    (0, __TURBOPACK__imported__module__$5b$externals$5d2f$react__$5b$external$5d$__$28$react$2c$__cjs$29$__["useEffect"])(()=>{
        const checkAuth = async ()=>{
            const token = ("TURBOPACK compile-time falsy", 0) ? "TURBOPACK unreachable" : null;
            if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
            ;
            setLoading(false);
        };
        checkAuth();
    }, []);
    const login = async (email, password, role)=>{
        try {
            // TODO: Update this endpoint to match your Django backend
            // Current Django endpoint: POST /login/ (returns rendered template)
            // Need to create: POST /api/auth/login/ (returns JSON with token)
            const response = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$js__$5b$ssr$5d$__$28$ecmascript$29$__["default"].post('/api/auth/login/', {
                email,
                password,
                role
            });
            // Assuming backend returns { token, user }
            if (response.token) {
                __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$js__$5b$ssr$5d$__$28$ecmascript$29$__["default"].setToken(response.token);
                setUser(response.user);
                return {
                    success: true
                };
            }
            throw new Error('Login failed - no token received');
        } catch (error) {
            console.error('Login error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    };
    const signup = async (userData)=>{
        try {
            // TODO: Update to match Django backend
            // Current: POST /signup/ (returns rendered template)
            // Need: POST /api/auth/signup/ (returns JSON)
            const response = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$js__$5b$ssr$5d$__$28$ecmascript$29$__["default"].post('/api/auth/signup/', userData);
            // Typically signup might auto-login or require email verification
            return {
                success: true,
                data: response
            };
        } catch (error) {
            console.error('Signup error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    };
    const logout = ()=>{
        __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$js__$5b$ssr$5d$__$28$ecmascript$29$__["default"].clearToken();
        setUser(null);
        if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
        ;
    };
    const value = {
        user,
        loading,
        login,
        signup,
        logout,
        isAuthenticated: !!user
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$externals$5d2f$react$2f$jsx$2d$dev$2d$runtime__$5b$external$5d$__$28$react$2f$jsx$2d$dev$2d$runtime$2c$__cjs$29$__["jsxDEV"])(AuthContext.Provider, {
        value: value,
        children: children
    }, void 0, false, {
        fileName: "[project]/context/AuthContext.js",
        lineNumber: 110,
        columnNumber: 10
    }, this);
} // SECURITY NOTE FOR DEVELOPERS:
 // This implementation uses localStorage for token storage which is vulnerable to XSS attacks.
 // For production:
 // 1. Consider using httpOnly cookies for token storage (requires backend changes)
 // 2. Implement token refresh mechanism
 // 3. Add CSRF protection
 // 4. Use secure, httpOnly, sameSite cookies
 // 5. Implement proper session management
 // 6. Add rate limiting on authentication endpoints
}),
"[project]/pages/_app.js [ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

// original: N/A - new Next.js app wrapper
__turbopack_context__.s([
    "default",
    ()=>__TURBOPACK__default__export__
]);
var __TURBOPACK__imported__module__$5b$externals$5d2f$react$2f$jsx$2d$dev$2d$runtime__$5b$external$5d$__$28$react$2f$jsx$2d$dev$2d$runtime$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/react/jsx-dev-runtime [external] (react/jsx-dev-runtime, cjs)");
var __TURBOPACK__imported__module__$5b$project$5d2f$context$2f$AuthContext$2e$js__$5b$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/context/AuthContext.js [ssr] (ecmascript)");
;
;
;
function MyApp({ Component, pageProps }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$externals$5d2f$react$2f$jsx$2d$dev$2d$runtime__$5b$external$5d$__$28$react$2f$jsx$2d$dev$2d$runtime$2c$__cjs$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$context$2f$AuthContext$2e$js__$5b$ssr$5d$__$28$ecmascript$29$__["AuthProvider"], {
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$externals$5d2f$react$2f$jsx$2d$dev$2d$runtime__$5b$external$5d$__$28$react$2f$jsx$2d$dev$2d$runtime$2c$__cjs$29$__["jsxDEV"])(Component, {
            ...pageProps
        }, void 0, false, {
            fileName: "[project]/pages/_app.js",
            lineNumber: 8,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/pages/_app.js",
        lineNumber: 7,
        columnNumber: 5
    }, this);
}
const __TURBOPACK__default__export__ = MyApp;
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__8c2b6b2f._.js.map