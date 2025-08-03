import streamlit as st
import streamlit.components.v1
import openai
from datetime import datetime
from uuid import uuid4
import base64
import requests
import time
import json
import hashlib
import pickle
import os
import glob
import re

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


def load_admin_settings():
    try:
        if not os.path.exists("database"):
            os.makedirs("database")
        if os.path.exists("database/admin_settings.json"):
            with open("database/admin_settings.json", "r") as f:
                return json.load(f)
        return {
            "api_key": st.secrets.get("OPENAI_API_KEY", ""),
            "system_prompt": "You are CatGPT, a helpful AI assistant. You have access to our previous conversation history and can reference past messages to provide contextual responses.",
            "memory_settings": {
                "max_context_messages": 20,
                "max_context_tokens": 4000,
                "summarize_old_context": True,
                "keep_important_messages": True
            },
            "global_image_generation": True,
            "app_config": {
                "app_title": "CatGPT",
                "app_icon": "🐱",
                "model_name": "CatGPT",
                "assistant_avatar": "🐱"
            }
        }
    except Exception:
        return {
            "api_key": st.secrets.get("OPENAI_API_KEY", ""),
            "system_prompt": "You are CatGPT, a helpful AI assistant. You have access to our previous conversation history and can reference past messages to provide contextual responses.",
            "memory_settings": {
                "max_context_messages": 20,
                "max_context_tokens": 4000,
                "summarize_old_context": True,
                "keep_important_messages": True
            },
            "global_image_generation": True,
            "app_config": {
                "app_title": "CatGPT",
                "app_icon": "🐱",
                "model_name": "CatGPT",
                "assistant_avatar": "🐱"
            }
        }


try:
    admin_settings = load_admin_settings()
    app_config = admin_settings.get("app_config", {})
    page_title = app_config.get("app_title", "CatGPT")
    page_icon = app_config.get("app_icon", "🐱")
except:
    page_title = "CatGPT"
    page_icon = "🐱"

st.set_page_config(
    page_title=page_title,
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)


def format_message_time():
    return datetime.now().strftime("%H:%M:%S")


def get_device_fingerprint():
    if 'device_fingerprint' not in st.session_state:
        fingerprint_key = f"device_fingerprint_{st.session_state.get('current_user', 'anonymous')}"

        if fingerprint_key not in st.session_state:
            st.session_state[fingerprint_key] = str(uuid4())

        st.session_state.device_fingerprint = st.session_state[fingerprint_key]

    return st.session_state.device_fingerprint


def generate_browser_fingerprint():
    fingerprint_js = """
    <script>
    function generateFingerprint() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('Device fingerprint', 2, 2);

        const fingerprint = {
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            screen: screen.width + 'x' + screen.height,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            canvas: canvas.toDataURL(),
            timestamp: Date.now()
        };

        const fingerprintString = JSON.stringify(fingerprint);
        const hash = btoa(fingerprintString).replace(/[^a-zA-Z0-9]/g, '').substring(0, 32);

        window.parent.postMessage({
            type: 'device_fingerprint',
            fingerprint: hash
        }, '*');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', generateFingerprint);
    } else {
        generateFingerprint();
    }
    </script>
    """

    st.components.v1.html(fingerprint_js, height=0)


def load_users():
    try:
        if not os.path.exists("database"):
            os.makedirs("database")
        if os.path.exists("database/users.json"):
            with open("database/users.json", "r") as f:
                users = json.load(f)

            for username in users:
                if "image_generation" not in users[username]:
                    users[username]["image_generation"] = {
                        "enabled": True,
                        "daily_limit": 10,
                        "usage_count": 0,
                        "last_reset": datetime.now().strftime("%Y-%m-%d")
                    }
            return users
        return {"team-engineers": {"name": "Team Engineers", "email": "team@lexdata.com", "password": "LexData Labs",
                                   "status": "active", "authorized_devices": [],
                                   "image_generation": {"enabled": True, "daily_limit": 10, "usage_count": 0,
                                                        "last_reset": datetime.now().strftime("%Y-%m-%d")}}}
    except Exception:
        return {"team-engineers": {"name": "Team Engineers", "email": "team@lexdata.com", "password": "LexData Labs",
                                   "status": "active", "authorized_devices": [],
                                   "image_generation": {"enabled": True, "daily_limit": 10, "usage_count": 0,
                                                        "last_reset": datetime.now().strftime("%Y-%m-%d")}}}


def save_global_chat_message(message):
    try:
        if not os.path.exists("database"):
            os.makedirs("database")

        global_chat_file = "database/global_chat.json"

        if os.path.exists(global_chat_file):
            with open(global_chat_file, "r") as f:
                global_chat = json.load(f)
        else:
            global_chat = {"messages": []}

        global_chat["messages"].append(message)

        if len(global_chat["messages"]) > 1000:
            global_chat["messages"] = global_chat["messages"][-1000:]

        with open(global_chat_file, "w") as f:
            json.dump(global_chat, f, indent=2)
    except Exception:
        pass


def load_global_chat():
    try:
        if not os.path.exists("database"):
            os.makedirs("database")

        global_chat_file = "database/global_chat.json"

        if os.path.exists(global_chat_file):
            with open(global_chat_file, "r") as f:
                global_chat = json.load(f)
            return global_chat.get("messages", [])
        return []
    except Exception:
        return []


def clear_global_chat():
    try:
        global_chat_file = "database/global_chat.json"
        if os.path.exists(global_chat_file):
            with open(global_chat_file, "w") as f:
                json.dump({"messages": []}, f, indent=2)
    except Exception:
        pass


def save_users(users):
    try:
        if not os.path.exists("database"):
            os.makedirs("database")
        with open("database/users.json", "w") as f:
            json.dump(users, f, indent=2)
    except Exception:
        pass
    try:
        if not os.path.exists("database"):
            os.makedirs("database")
        with open("database/users.json", "w") as f:
            json.dump(users, f, indent=2)
    except Exception:
        pass


def check_image_generation_limit(username):
    admin_settings = load_admin_settings()
    global_image_enabled = admin_settings.get("global_image_generation", True)

    if not global_image_enabled:
        return False, "Image generation is globally disabled by admin"

    users = load_users()
    if username not in users:
        return False, "User not found"

    user_data = users[username]
    image_settings = user_data.get("image_generation", {"enabled": True, "daily_limit": 10, "usage_count": 0,
                                                        "last_reset": datetime.now().strftime("%Y-%m-%d")})

    if not image_settings.get("enabled", True):
        return False, "Image generation is disabled for this user"

    today = datetime.now().strftime("%Y-%m-%d")
    last_reset = image_settings.get("last_reset", today)

    if last_reset != today:
        image_settings["usage_count"] = 0
        image_settings["last_reset"] = today
        users[username]["image_generation"] = image_settings
        save_users(users)

    usage_count = image_settings.get("usage_count", 0)
    daily_limit = image_settings.get("daily_limit", 10)

    if usage_count >= daily_limit:
        return False, f"Daily image generation limit reached ({usage_count}/{daily_limit})"

    return True, f"Images remaining: {daily_limit - usage_count}"


def increment_image_usage(username):
    users = load_users()
    if username in users:
        image_settings = users[username].get("image_generation", {"enabled": True, "daily_limit": 10, "usage_count": 0,
                                                                  "last_reset": datetime.now().strftime("%Y-%m-%d")})

        today = datetime.now().strftime("%Y-%m-%d")
        if image_settings.get("last_reset", today) != today:
            image_settings["usage_count"] = 0
            image_settings["last_reset"] = today

        image_settings["usage_count"] = image_settings.get("usage_count", 0) + 1
        users[username]["image_generation"] = image_settings
        save_users(users)


def save_admin_settings(settings):
    try:
        if not os.path.exists("database"):
            os.makedirs("database")
        with open("database/admin_settings.json", "w") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def save_session_data():
    try:
        if not os.path.exists("database"):
            os.makedirs("database")
        device_fingerprint = get_device_fingerprint()
        session_data = {
            "authenticated": st.session_state.get("authenticated", False),
            "current_user": st.session_state.get("current_user", None),
            "is_admin": st.session_state.get("is_admin", False),
            "device_fingerprint": device_fingerprint,
            "last_access": datetime.now().isoformat(),
            "session_id": str(uuid4())
        }
        session_file = f"database/session_{device_fingerprint}.json"
        with open(session_file, "w") as f:
            json.dump(session_data, f)

        st.session_state.session_saved = True
    except Exception:
        pass


def load_session_data():
    try:
        if not os.path.exists("database"):
            os.makedirs("database")

        device_fingerprint = get_device_fingerprint()
        session_file = f"database/session_{device_fingerprint}.json"

        if os.path.exists(session_file):
            with open(session_file, "r") as f:
                session_data = json.load(f)

            stored_fingerprint = session_data.get("device_fingerprint", "")
            last_access = session_data.get("last_access", "")

            try:
                if last_access:
                    access_time = datetime.fromisoformat(last_access.replace('Z', '+00:00'))
                    if (datetime.now() - access_time).total_seconds() > 86400:
                        os.remove(session_file)
                        st.session_state.authenticated = False
                        st.session_state.current_user = None
                        st.session_state.is_admin = False
                        return
            except:
                pass

            if device_fingerprint == stored_fingerprint:
                st.session_state.authenticated = session_data.get("authenticated", False)
                st.session_state.current_user = session_data.get("current_user", None)
                st.session_state.is_admin = session_data.get("is_admin", False)
            else:
                st.session_state.authenticated = False
                st.session_state.current_user = None
                st.session_state.is_admin = False
                try:
                    os.remove(session_file)
                except:
                    pass
        else:
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.is_admin = False
    except Exception:
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.session_state.is_admin = False


def authorize_device_for_user(username, device_fingerprint):
    users = load_users()
    if username in users:
        if "authorized_devices" not in users[username]:
            users[username]["authorized_devices"] = []

        device_info = {
            "fingerprint": device_fingerprint,
            "authorized_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        }

        existing_device = None
        for i, device in enumerate(users[username]["authorized_devices"]):
            if device["fingerprint"] == device_fingerprint:
                existing_device = i
                break

        if existing_device is not None:
            users[username]["authorized_devices"][existing_device]["last_used"] = datetime.now().isoformat()
        else:
            users[username]["authorized_devices"].append(device_info)

        save_users(users)


def is_device_authorized(username, device_fingerprint):
    users = load_users()
    if username in users:
        authorized_devices = users[username].get("authorized_devices", [])
        for device in authorized_devices:
            if device["fingerprint"] == device_fingerprint:
                return True
    return False


def check_authentication():
    if 'browser_fingerprint_generated' not in st.session_state:
        generate_browser_fingerprint()
        st.session_state.browser_fingerprint_generated = True

    load_session_data()
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if st.session_state.authenticated and st.session_state.current_user:
        device_fingerprint = get_device_fingerprint()
        if not is_device_authorized(st.session_state.current_user,
                                    device_fingerprint) and not st.session_state.is_admin:
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.is_admin = False
            try:
                session_file = f"database/session_{device_fingerprint}.json"
                if os.path.exists(session_file):
                    os.remove(session_file)
            except:
                pass
            return False

    return st.session_state.authenticated


def login_form():
    if "show_signup" not in st.session_state:
        st.session_state.show_signup = False

    admin_settings = load_admin_settings()
    app_config = admin_settings.get("app_config", {})
    app_title = app_config.get("app_title", "CatGPT")

    st.markdown(f"""
        <div style='text-align: center; margin-bottom: 2rem;'>
            <h1>{app_title}</h1>
            <p style='color: #666; font-size: 1.1rem;'>Please login or signup to access {app_title}</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2, tab3 = st.tabs(["Login", "Sign Up", "Admin"])

        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter username")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                login_button = st.form_submit_button("Login", use_container_width=True)

                if login_button:
                    users = load_users()
                    if username in users and users[username]["password"] == password:
                        if users[username].get("status", "active") == "blocked":
                            st.error("Your account has been blocked. Please contact admin.")
                        else:
                            device_fingerprint = get_device_fingerprint()
                            if not is_device_authorized(username, device_fingerprint):
                                authorize_device_for_user(username, device_fingerprint)
                                st.info(f"New device detected. This device has been authorized for future logins.")
                            else:
                                authorize_device_for_user(username, device_fingerprint)

                            st.session_state.authenticated = True
                            st.session_state.current_user = username
                            st.session_state.is_admin = False
                            save_session_data()
                            st.success("Login successful! Redirecting...")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("Invalid username or password")

        with tab2:
            with st.form("signup_form"):
                new_name = st.text_input("Full Name", placeholder="Enter your full name")
                new_email = st.text_input("Email", placeholder="Enter your email")
                new_username = st.text_input("Username", placeholder="Choose a username")
                new_password = st.text_input("Password", type="password", placeholder="Choose a password")
                signup_button = st.form_submit_button("Sign Up", use_container_width=True)

                if signup_button:
                    if new_name and new_email and new_username and new_password:
                        users = load_users()
                        if new_username not in users:
                            device_fingerprint = get_device_fingerprint()
                            users[new_username] = {
                                "name": new_name,
                                "email": new_email,
                                "password": new_password,
                                "status": "active",
                                "authorized_devices": [{
                                    "fingerprint": device_fingerprint,
                                    "authorized_at": datetime.now().isoformat(),
                                    "last_used": datetime.now().isoformat()
                                }],
                                "image_generation": {
                                    "enabled": True,
                                    "daily_limit": 10,
                                    "usage_count": 0,
                                    "last_reset": datetime.now().strftime("%Y-%m-%d")
                                }
                            }
                            save_users(users)
                            st.session_state.authenticated = True
                            st.session_state.current_user = new_username
                            st.session_state.is_admin = False
                            save_session_data()
                            st.success("Account created successfully! Logging you in...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Username already exists")
                    else:
                        st.error("Please fill in all fields")

        with tab3:
            with st.form("admin_form"):
                admin_username = st.text_input("Admin Username", placeholder="Enter admin username")
                admin_password = st.text_input("Admin Password", type="password", placeholder="Enter admin password")
                admin_login_button = st.form_submit_button("Admin Login", use_container_width=True)

                if admin_login_button:
                    if admin_username == "shuvo" and admin_password == "Super Admin007":
                        st.session_state.authenticated = True
                        st.session_state.current_user = "shuvo"
                        st.session_state.is_admin = True
                        save_session_data()
                        st.success("Admin login successful! Redirecting...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Invalid admin credentials")


def logout():
    device_fingerprint = get_device_fingerprint()
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.is_admin = False
    try:
        session_file = f"database/session_{device_fingerprint}.json"
        if os.path.exists(session_file):
            os.remove(session_file)
    except Exception:
        pass

    for key in list(st.session_state.keys()):
        if key.startswith('device_fingerprint_'):
            del st.session_state[key]

    for key in list(st.session_state.keys()):
        if key not in ["authenticated", "current_user", "is_admin"]:
            del st.session_state[key]
    st.rerun()


def save_data_to_file():
    if "current_user" not in st.session_state:
        return

    if not os.path.exists("database"):
        os.makedirs("database")
    user_data_file = f"database/catgpt_data_{st.session_state.current_user}.json"
    data_to_save = {
        "chat_history": st.session_state.get("chat_history", []),
        "chat_sessions": st.session_state.get("chat_sessions", {}),
        "current_session_id": st.session_state.get("current_session_id", str(uuid4())),
        "model": st.session_state.get("model", "gpt-4o-mini"),
        "total_tokens": st.session_state.get("total_tokens", 0),
        "message_count": st.session_state.get("message_count", 0)
    }

    try:
        with open(user_data_file, "w") as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        pass


def load_data_from_file():
    if "current_user" not in st.session_state:
        return

    if not os.path.exists("database"):
        os.makedirs("database")
    user_data_file = f"database/catgpt_data_{st.session_state.current_user}.json"
    try:
        if os.path.exists(user_data_file):
            with open(user_data_file, "r") as f:
                data = json.load(f)

            st.session_state.chat_history = data.get("chat_history", [])
            st.session_state.chat_sessions = data.get("chat_sessions", {})
            st.session_state.current_session_id = data.get("current_session_id", str(uuid4()))
            st.session_state.model = data.get("model", "gpt-4o-mini")
            st.session_state.total_tokens = data.get("total_tokens", 0)
            st.session_state.message_count = data.get("message_count", 0)
    except Exception as e:
        pass


def admin_panel():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🔧 Admin Panel")
    with col2:
        if st.button("Logout", use_container_width=True):
            logout()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["API Settings", "User Management", "Chat History", "Memory Settings", "App Configuration"])

    with tab1:
        st.subheader("OpenAI API Key Management")
        admin_settings = load_admin_settings()
        current_api_key = admin_settings.get("api_key", "")

        with st.form("api_key_form"):
            new_api_key = st.text_input("OpenAI API Key", value=current_api_key, type="password")
            if st.form_submit_button("Update API Key"):
                admin_settings["api_key"] = new_api_key
                save_admin_settings(admin_settings)
                openai.api_key = new_api_key
                st.success("API Key updated successfully!")
                st.rerun()

        if current_api_key:
            st.success("API Key is configured")
        else:
            st.error("No API Key configured")

    with tab2:
        st.subheader("User Management")

        admin_settings = load_admin_settings()
        global_image_enabled = admin_settings.get("global_image_generation", True)

        st.markdown("**Global Image Generation Control**")
        col1_global, col2_global = st.columns([1, 3])

        with col1_global:
            new_global_state = st.checkbox(
                "Enable Image Generation Globally",
                value=global_image_enabled,
                help="Master switch to enable/disable image generation for all users"
            )

            if new_global_state != global_image_enabled:
                admin_settings["global_image_generation"] = new_global_state
                save_admin_settings(admin_settings)
                if new_global_state:
                    st.success("✅ Image generation enabled globally!")
                else:
                    st.warning("🚫 Image generation disabled globally!")
                st.rerun()

        with col2_global:
            if global_image_enabled:
                st.success("🟢 Image generation is globally enabled")
            else:
                st.error("🔴 Image generation is globally disabled")

        st.divider()

        users = load_users()

        if users:
            for username, user_data in users.items():
                if username == "shuvo":
                    continue

                col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1, 1, 1])

                with col1:
                    st.write(f"**{user_data['name']}** ({username})")
                    st.caption(user_data['email'])
                    authorized_devices = user_data.get('authorized_devices', [])
                    if authorized_devices:
                        device_count = len(authorized_devices)
                        st.caption(f"Authorized devices: {device_count}")
                        if device_count > 0:
                            latest_device = max(authorized_devices, key=lambda x: x.get('last_used', ''))
                            last_used = latest_device.get('last_used', 'Unknown')
                            if last_used != 'Unknown':
                                try:
                                    last_used_dt = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
                                    last_used = last_used_dt.strftime('%m/%d %H:%M')
                                except:
                                    pass
                            st.caption(f"Last used: {last_used}")
                    else:
                        st.caption("No authorized devices")

                with col2:
                    status = user_data.get('status', 'active')
                    if status == 'active':
                        st.success("🟢 Active")
                    else:
                        st.error("🔴 Blocked")

                with col3:
                    user_data_file = f"database/catgpt_data_{username}.json"
                    current_model = "gpt-4o-mini"
                    if os.path.exists(user_data_file):
                        try:
                            with open(user_data_file, "r") as f:
                                data = json.load(f)
                            current_model = data.get("model", "gpt-4o-mini")
                        except:
                            pass

                    new_model = st.selectbox(
                        "Model",
                        ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4-turbo"],
                        index=["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4-turbo"].index(current_model),
                        key=f"model_{username}"
                    )

                    if new_model != current_model:
                        try:
                            if os.path.exists(user_data_file):
                                with open(user_data_file, "r") as f:
                                    data = json.load(f)
                                data["model"] = new_model
                                with open(user_data_file, "w") as f:
                                    json.dump(data, f, indent=2)
                        except:
                            pass

                with col4:
                    if user_data.get('status', 'active') == 'active':
                        if st.button("Block", key=f"block_{username}"):
                            users[username]['status'] = 'blocked'
                            save_users(users)
                            st.rerun()
                    else:
                        if st.button("Unblock", key=f"unblock_{username}"):
                            users[username]['status'] = 'active'
                            save_users(users)
                            st.rerun()

                with col5:
                    if st.button("Delete", key=f"delete_{username}"):
                        del users[username]
                        save_users(users)
                        try:
                            user_file = f"database/catgpt_data_{username}.json"
                            if os.path.exists(user_file):
                                os.remove(user_file)
                        except:
                            pass
                        st.rerun()

                st.markdown("**Image Generation Settings**")

                image_settings = user_data.get("image_generation",
                                               {"enabled": True, "daily_limit": 10, "usage_count": 0,
                                                "last_reset": datetime.now().strftime("%Y-%m-%d")})

                col1_img, col2_img, col3_img = st.columns([1, 1, 1])

                with col1_img:
                    if not global_image_enabled:
                        st.error("🚫 Globally Disabled")
                        st.caption("Enable global image generation first")
                    else:
                        image_enabled = st.checkbox(
                            "Enable Image Generation",
                            value=image_settings.get("enabled", True),
                            key=f"img_enabled_{username}"
                        )
                        if image_enabled != image_settings.get("enabled", True):
                            users[username]["image_generation"]["enabled"] = image_enabled
                            save_users(users)
                            st.rerun()

                with col2_img:
                    if not global_image_enabled:
                        st.text_input("Daily Limit", value=str(image_settings.get("daily_limit", 10)), disabled=True,
                                      key=f"disabled_limit_{username}")
                    else:
                        daily_limit = st.number_input(
                            "Daily Limit",
                            min_value=0,
                            max_value=100,
                            value=image_settings.get("daily_limit", 10),
                            key=f"img_limit_{username}"
                        )
                        if daily_limit != image_settings.get("daily_limit", 10):
                            users[username]["image_generation"]["daily_limit"] = daily_limit
                            save_users(users)
                            st.rerun()

                with col3_img:
                    usage_count = image_settings.get("usage_count", 0)
                    daily_limit = image_settings.get("daily_limit", 10)
                    st.metric("Today's Usage", f"{usage_count}/{daily_limit}")
                    if not global_image_enabled:
                        st.button("Reset Count", disabled=True, key=f"disabled_reset_{username}")
                    else:
                        if st.button("Reset Count", key=f"reset_img_{username}"):
                            users[username]["image_generation"]["usage_count"] = 0
                            users[username]["image_generation"]["last_reset"] = datetime.now().strftime("%Y-%m-%d")
                            save_users(users)
                            st.rerun()

                if st.button(f"Reset Devices for {username}", key=f"reset_devices_{username}"):
                    users[username]['authorized_devices'] = []
                    save_users(users)

                    for session_file in glob.glob(f"database/session_*.json"):
                        try:
                            with open(session_file, 'r') as f:
                                session_data = json.load(f)
                            if session_data.get('current_user') == username:
                                os.remove(session_file)
                        except:
                            pass

                    st.success(f"All authorized devices cleared for {username}")
                    st.rerun()

                st.divider()
        else:
            st.info("No users found")

        st.markdown("---")
        st.subheader("Global Chat Management")

        global_messages = load_global_chat()

        col1_global, col2_global = st.columns([1, 1])
        with col1_global:
            st.metric("Total Global Messages", len(global_messages))
        with col2_global:
            if st.button("Clear Global Chat", type="secondary"):
                clear_global_chat()
                st.success("Global chat cleared!")
                st.rerun()

        if global_messages:
            st.write("**Recent Global Messages (Last 10):**")
            for msg in global_messages[-10:]:
                timestamp = msg.get("timestamp", "Unknown")
                content = msg.get("content", "")
                if len(content) > 100:
                    content = content[:100] + "..."
                st.text(f"[{timestamp}] {content}")

    with tab3:
        st.subheader("All User Chat Histories")
        users = load_users()

        selected_user = st.selectbox("Select User", list(users.keys()))

        if selected_user:
            user_data_file = f"database/catgpt_data_{selected_user}.json"

            if os.path.exists(user_data_file):
                try:
                    with open(user_data_file, "r") as f:
                        user_data = json.load(f)

                    chat_history = user_data.get("chat_history", [])
                    chat_sessions = user_data.get("chat_sessions", {})

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Messages", len(chat_history))
                        st.metric("Total Sessions", len(chat_sessions))
                    with col2:
                        st.metric("Total Tokens", user_data.get("total_tokens", 0))
                        st.metric("Model Used", user_data.get("model", "N/A"))

                    if chat_sessions:
                        st.subheader("Sessions")
                        session_options = {f"{session['name']} ({session_id[:8]}...)": session_id
                                           for session_id, session in chat_sessions.items()}
                        selected_session = st.selectbox("Select Session", list(session_options.keys()))

                        if selected_session:
                            session_id = session_options[selected_session]
                            session_data = chat_sessions[session_id]

                            st.write(f"**Created:** {session_data.get('created_at', 'Unknown')}")
                            st.write(f"**Messages:** {session_data.get('message_count', 0)}")

                            st.subheader("Messages")
                            for msg in session_data.get('messages', []):
                                with st.chat_message(msg["role"]):
                                    if msg["content"].startswith("![Generated Image](http"):
                                        url = msg["content"].split("(")[1].rstrip(")")
                                        try:
                                            st.image(url, caption="Generated Image", use_column_width=True)
                                        except:
                                            st.error("Failed to load image")
                                    else:
                                        st.markdown(msg["content"])

                                    if "timestamp" in msg:
                                        st.caption(f"Time: {msg['timestamp']}")

                    if chat_history and not chat_sessions:
                        st.subheader("Current Session Messages")
                        for msg in chat_history:
                            with st.chat_message(msg["role"]):
                                if msg["content"].startswith("![Generated Image](http"):
                                    url = msg["content"].split("(")[1].rstrip(")")
                                    try:
                                        st.image(url, caption="Generated Image", use_column_width=True)
                                    except:
                                        st.error("Failed to load image")
                                else:
                                    st.markdown(msg["content"])

                                if "timestamp" in msg:
                                    st.caption(f"Time: {msg['timestamp']}")

                    if st.button(f"Delete {selected_user}'s Chat Data"):
                        try:
                            os.remove(user_data_file)
                            st.success(f"Chat data for {selected_user} has been deleted!")
                            st.rerun()
                        except:
                            st.error("Failed to delete chat data")

                except Exception as e:
                    st.error(f"Error loading chat data: {str(e)}")
            else:
                st.info(f"No chat data found for {selected_user}")

    with tab4:
        st.subheader("Memory & System Settings (Global)")
        admin_settings = load_admin_settings()

        st.write("**Memory Settings**")
        max_context_messages = st.slider(
            "Max Context Messages",
            min_value=5,
            max_value=50,
            value=admin_settings["memory_settings"]["max_context_messages"],
            help="Maximum number of messages to keep in context"
        )
        if max_context_messages != admin_settings["memory_settings"]["max_context_messages"]:
            admin_settings["memory_settings"]["max_context_messages"] = max_context_messages
            save_admin_settings(admin_settings)
            st.success("Memory settings updated!")

        max_context_tokens = st.slider(
            "Max Context Tokens",
            min_value=2000,
            max_value=15000,
            value=admin_settings["memory_settings"]["max_context_tokens"],
            step=1000,
            help="Maximum tokens to keep in context"
        )
        if max_context_tokens != admin_settings["memory_settings"]["max_context_tokens"]:
            admin_settings["memory_settings"]["max_context_tokens"] = max_context_tokens
            save_admin_settings(admin_settings)
            st.success("Memory settings updated!")

        summarize_old_context = st.checkbox(
            "Auto-summarize old messages",
            value=admin_settings["memory_settings"]["summarize_old_context"],
            help="Automatically create summaries of older messages"
        )
        if summarize_old_context != admin_settings["memory_settings"]["summarize_old_context"]:
            admin_settings["memory_settings"]["summarize_old_context"] = summarize_old_context
            save_admin_settings(admin_settings)
            st.success("Memory settings updated!")

        st.markdown("---")
        st.write("**System Prompt**")
        system_prompt = st.text_area(
            "Customize how CatGPT behaves",
            value=admin_settings.get("system_prompt",
                                     "You are CatGPT, a helpful AI assistant. You have access to our previous conversation history and can reference past messages to provide contextual responses."),
            height=200,
            help="Define CatGPT's personality and behavior"
        )
        if system_prompt != admin_settings.get("system_prompt", ""):
            admin_settings["system_prompt"] = system_prompt
            save_admin_settings(admin_settings)
            st.success("System prompt updated!")

    with tab5:
        st.subheader("Application Configuration")
        admin_settings = load_admin_settings()
        app_config = admin_settings.get("app_config", {
            "app_title": "CatGPT",
            "app_icon": "🐱",
            "model_name": "CatGPT",
            "assistant_avatar": "🐱"
        })

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Application Settings**")

            new_app_title = st.text_input(
                "Application Title",
                value=app_config.get("app_title", "CatGPT"),
                help="This will appear in browser tab and throughout the app"
            )

            new_app_icon = st.text_input(
                "Application Icon (Browser Tab)",
                value=app_config.get("app_icon", "🐱"),
                help="Emoji or character that appears in browser tab"
            )

            new_model_name = st.text_input(
                "Model Display Name",
                value=app_config.get("model_name", "CatGPT"),
                help="Name shown to users when interacting with the AI"
            )

            new_assistant_avatar = st.text_input(
                "Assistant Avatar",
                value=app_config.get("assistant_avatar", "🐱"),
                help="Emoji or character shown next to assistant messages"
            )

        with col2:
            st.markdown("**Preview**")
            st.markdown(f"**Browser Tab:** {new_app_icon} {new_app_title}")
            st.markdown(f"**Model Name:** {new_model_name}")
            st.markdown(f"**Assistant Avatar:** {new_assistant_avatar}")

            st.markdown("**Chat Preview:**")
            with st.chat_message("assistant", avatar=new_assistant_avatar):
                st.markdown(f"Hello! I'm {new_model_name}, your AI assistant. How can I help you today?")

        if (new_app_title != app_config.get("app_title", "CatGPT") or
                new_app_icon != app_config.get("app_icon", "🐱") or
                new_model_name != app_config.get("model_name", "CatGPT") or
                new_assistant_avatar != app_config.get("assistant_avatar", "🐱")):

            if st.button("Update Application Configuration", use_container_width=True):
                admin_settings["app_config"] = {
                    "app_title": new_app_title,
                    "app_icon": new_app_icon,
                    "model_name": new_model_name,
                    "assistant_avatar": new_assistant_avatar
                }
                save_admin_settings(admin_settings)
                st.success("Application configuration updated! Please refresh the page to see all changes.")
                st.balloons()

        st.markdown("---")
        st.markdown("**Reset to Defaults**")
        col1_reset, col2_reset = st.columns([1, 3])

        with col1_reset:
            if st.button("Reset to Defaults"):
                admin_settings["app_config"] = {
                    "app_title": "CatGPT",
                    "app_icon": "🐱",
                    "model_name": "CatGPT",
                    "assistant_avatar": "🐱"
                }
                save_admin_settings(admin_settings)
                st.success("Reset to default configuration! Please refresh the page.")
                st.rerun()

        with col2_reset:
            st.caption("This will reset all app configuration to original CatGPT settings")


def global_chat_interface():
    admin_settings = load_admin_settings()
    app_config = admin_settings.get("app_config", {})
    app_title = app_config.get("app_title", "CatGPT")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"🌐 {app_title} Global Chat")
        st.caption("Chat with all users in real-time • Your messages on right, others on left")
    with col2:
        if st.button("← Back to Personal Chat", use_container_width=True):
            st.session_state.show_global_chat = False
            st.rerun()

    st.markdown("---")

    st.markdown("""
    <style>
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }
    .message-row-right {
        display: flex;
        justify-content: flex-end;
        width: 100%;
    }
    .message-row-left {
        display: flex;
        justify-content: flex-start;
        width: 100%;
    }
    .message-content {
        max-width: 70%;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin: 0.25rem;
        background-color: var(--background-color);
        border: 1px solid var(--border-color);
        color: var(--text-color);
    }
    .message-time {
        font-size: 0.8rem;
        color: var(--secondary-text-color);
        margin-top: 0.25rem;
    }

    /* Light mode */
    [data-theme="light"] .message-content {
        --background-color: #f8f9fa;
        --border-color: #e9ecef;
        --text-color: #333;
        --secondary-text-color: #666;
    }

    /* Dark mode */
    [data-theme="dark"] .message-content,
    .stApp[data-theme="dark"] .message-content,
    .message-content {
        background-color: #2b2b2b !important;
        border: 1px solid #404040 !important;
        color: #ffffff !important;
    }

    [data-theme="dark"] .message-time,
    .stApp[data-theme="dark"] .message-time,
    .message-time {
        color: #cccccc !important;
    }

    /* Fallback for any theme */
    @media (prefers-color-scheme: dark) {
        .message-content {
            background-color: #2b2b2b !important;
            border: 1px solid #404040 !important;
            color: #ffffff !important;
        }
        .message-time {
            color: #cccccc !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    if "global_auto_refresh" not in st.session_state:
        st.session_state.global_auto_refresh = True

    if "last_global_check" not in st.session_state:
        st.session_state.last_global_check = time.time()

    current_time = time.time()
    time_since_last_check = current_time - st.session_state.last_global_check

    if time_since_last_check >= 3:
        st.session_state.last_global_check = current_time
        st.rerun()

    global_messages = load_global_chat()
    current_user = st.session_state.get("current_user", "")

    if global_messages:
        st.subheader("💬 Global Conversation")

        col1_status, col2_status = st.columns([2, 1])
        with col1_status:
            st.info(f"📊 {len(global_messages)} messages • 🔄 Auto-refresh: ON")
        with col2_status:
            current_time_str = datetime.now().strftime("%H:%M:%S")
            st.caption(f"Last update: {current_time_str}")

        st.markdown('<div class="chat-container">', unsafe_allow_html=True)

        for message in global_messages[-50:]:
            content = message.get("content", "")
            timestamp = message.get("timestamp", "")
            message_user = message.get("user_id", "")

            is_current_user = (message_user == current_user)

            if is_current_user:
                st.markdown(f"""
                <div class="message-row-right">
                    <div class="message-content">
                        <div>{content}</div>
                        <div class="message-time">🕐 {timestamp}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="message-row-left">
                    <div class="message-content">
                        <div>{content}</div>
                        <div class="message-time">🕐 {timestamp}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    else:
        st.info("🌟 Be the first to start the global conversation!")
        st.markdown("**Welcome to Global Chat!**")
        st.markdown("- Chat with all logged-in users")
        st.markdown("- Your messages appear on the right (gray)")
        st.markdown("- Others' messages appear on the left (gray)")
        st.markdown("- New messages appear automatically every 3 seconds")

    if global_prompt := st.chat_input("Type your message to the global chat..."):
        user_message = {
            "role": "user",
            "content": global_prompt,
            "timestamp": format_message_time(),
            "message_id": str(uuid4()),
            "user_id": current_user
        }

        save_global_chat_message(user_message)
        st.session_state.last_global_check = time.time()
        st.rerun()

    time.sleep(3)
    st.rerun()


def initialize_session_state():
    admin_settings = load_admin_settings()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = {}
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = str(uuid4())
    if "model" not in st.session_state:
        st.session_state.model = "gpt-4o-mini"
    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0
    if "message_count" not in st.session_state:
        st.session_state.message_count = 0
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = admin_settings.get("system_prompt",
                                                            "You are CatGPT, a helpful AI assistant. You have access to our previous conversation history and can reference past messages to provide contextual responses.")
    if "memory_settings" not in st.session_state:
        st.session_state.memory_settings = admin_settings.get("memory_settings", {
            "max_context_messages": 20,
            "max_context_tokens": 4000,
            "summarize_old_context": True,
            "keep_important_messages": True
        })
    if "show_global_chat" not in st.session_state:
        st.session_state.show_global_chat = False


def detect_image_request(prompt):
    image_keywords = [
        'generate image', 'create image', 'make image', 'draw', 'sketch', 'paint', 'illustration',
        'picture of', 'image of', 'photo of', 'artwork', 'design', 'visualize', 'show me',
        'generate a', 'create a', 'make a', 'draw a', 'paint a', 'design a'
    ]

    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in image_keywords)


def generate_dalle_image(prompt):
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1,
        )

        image_url = response.data[0].url
        return image_url
    except Exception as e:
        raise Exception(f"Failed to generate image: {str(e)}")


initialize_session_state()

if not check_authentication():
    login_form()
    st.stop()

if st.session_state.is_admin:
    admin_panel()
    st.stop()

if st.session_state.get("show_global_chat", False):
    global_chat_interface()
    st.stop()

if st.session_state.get("authenticated") and st.session_state.get("current_user"):
    load_data_from_file()
    save_data_to_file()


@st.cache_data
def load_custom_css():
    return """
    <style>
    .main > div {
        padding-top: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #f0f2f6;
        border-left: 4px solid #ff6b6b;
    }
    .assistant-message {
        background-color: #e8f4fd;
        border-left: 4px solid #4dabf7;
    }
    .system-message {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        font-style: italic;
    }
    .message-time {
        font-size: 0.75rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .model-badge {
        background-color: #28a745;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        margin-bottom: 0.5rem;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .chat-stats {
        font-size: 0.8rem;
        color: #666;
        text-align: center;
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .memory-indicator {
        background-color: #e3f2fd;
        border: 1px solid #2196f3;
        border-radius: 0.5rem;
        padding: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    .context-warning {
        background-color: #fff3e0;
        border: 1px solid #ff9800;
        border-radius: 0.5rem;
        padding: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    </style>
    """


st.markdown(load_custom_css(), unsafe_allow_html=True)


def get_token_count(text, model="gpt-4"):
    if TIKTOKEN_AVAILABLE:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            pass

    word_count = len(text.split())
    char_count = len(text)
    token_estimate_words = int(word_count * 1.3)
    token_estimate_chars = int(char_count / 4)
    return max(token_estimate_words, token_estimate_chars)


def get_conversation_token_count(messages):
    total_tokens = 0
    for message in messages:
        total_tokens += get_token_count(message["content"])
    return int(total_tokens)


admin_settings = load_admin_settings()
api_key = admin_settings.get("api_key", st.secrets.get("OPENAI_API_KEY", ""))

try:
    openai.api_key = api_key
    if not openai.api_key:
        st.error("OpenAI API key not found. Please contact admin to configure the API key.")
        st.stop()
except Exception as e:
    st.error("Error loading OpenAI API key. Please check your configuration.")
    st.stop()


def create_conversation_summary(messages):
    if len(messages) < 3:
        return ""

    conversation_text = ""
    for msg in messages[-10:]:
        if msg["role"] != "system":
            conversation_text += f"{msg['role']}: {msg['content'][:200]}...\n"

    summary_messages = [
        {"role": "system",
         "content": "Create a brief 1-2 sentence summary of the key topics and context from this conversation that would help continue the discussion."},
        {"role": "user", "content": f"Summarize this conversation:\n{conversation_text}"}
    ]

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=summary_messages,
            max_tokens=100,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except:
        topics = []
        for msg in messages[-5:]:
            if msg["role"] == "user" and len(msg["content"]) > 10:
                words = msg["content"].split()[:8]
                topics.append(" ".join(words))
        if topics:
            return f"Previous discussion about: {', '.join(topics[:2])}"
        return "Previous conversation context available"


def manage_conversation_memory(messages):
    admin_settings = load_admin_settings()
    memory_settings = admin_settings.get("memory_settings", {
        "max_context_messages": 20,
        "max_context_tokens": 4000,
        "summarize_old_context": True,
        "keep_important_messages": True
    })

    max_messages = memory_settings["max_context_messages"]
    max_tokens = memory_settings["max_context_tokens"]

    all_context_messages = []

    if st.session_state.chat_sessions:
        for session_id, session_data in list(st.session_state.chat_sessions.items())[-3:]:
            if session_id != st.session_state.current_session_id:
                session_messages = session_data.get('messages', [])
                if session_messages:
                    session_summary = create_conversation_summary(session_messages)
                    if session_summary:
                        all_context_messages.append({
                            "role": "system",
                            "content": f"[Session {session_data.get('name', 'Previous')}: {session_summary}]",
                            "timestamp": format_message_time()
                        })

    current_messages = messages.copy()

    if len(current_messages) > max_messages:
        if memory_settings["summarize_old_context"]:
            old_messages = current_messages[:-max_messages]
            recent_messages = current_messages[-max_messages:]

            summary = create_conversation_summary(old_messages)
            if summary:
                summary_message = {"role": "system", "content": summary, "timestamp": format_message_time()}
                current_messages = [summary_message] + recent_messages
        else:
            current_messages = current_messages[-max_messages:]

    final_messages = all_context_messages + current_messages

    total_tokens = get_conversation_token_count(final_messages)
    if total_tokens > max_tokens:
        if all_context_messages:
            final_messages = all_context_messages[-1:] + current_messages
        else:
            final_messages = current_messages

    return final_messages


def save_current_session():
    session_data = {
        "id": st.session_state.current_session_id,
        "name": f"Chat {datetime.now().strftime('%m/%d %H:%M')}",
        "messages": st.session_state.chat_history.copy(),
        "model": st.session_state.model,
        "created_at": datetime.now().isoformat(),
        "message_count": st.session_state.message_count,
        "total_tokens": st.session_state.total_tokens
    }
    st.session_state.chat_sessions[st.session_state.current_session_id] = session_data
    save_data_to_file()


def load_session(session_id):
    if session_id in st.session_state.chat_sessions:
        session = st.session_state.chat_sessions[session_id]
        st.session_state.chat_history = session["messages"]
        st.session_state.current_session_id = session_id
        st.session_state.model = session.get("model", "gpt-4o-mini")
        st.session_state.message_count = session.get("message_count", 0)
        st.session_state.total_tokens = session.get("total_tokens", 0)
        save_data_to_file()
        st.success(f"Loaded session: {session['name']}")
        time.sleep(1)
        st.rerun()


def create_new_session():
    save_current_session()
    st.session_state.chat_history = []
    st.session_state.current_session_id = str(uuid4())
    st.session_state.message_count = 0
    st.session_state.total_tokens = 0
    save_data_to_file()
    st.success("New chat session created!")
    time.sleep(1)
    st.rerun()


def export_chat():
    if st.session_state.chat_history:
        chat_data = {
            "session_id": st.session_state.current_session_id,
            "model": st.session_state.model,
            "timestamp": datetime.now().isoformat(),
            "messages": st.session_state.chat_history,
            "total_tokens": st.session_state.total_tokens,
            "system_prompt": st.session_state.system_prompt,
            "memory_settings": st.session_state.memory_settings
        }
        return json.dumps(chat_data, indent=2)
    return None


def clear_chat():
    st.session_state.chat_history = []
    st.session_state.current_session_id = str(uuid4())
    st.session_state.total_tokens = 0
    st.session_state.message_count = 0
    save_data_to_file()
    st.success("Chat cleared successfully!")
    time.sleep(1)
    st.rerun()


def display_message(message):
    admin_settings = load_admin_settings()
    app_config = admin_settings.get("app_config", {})
    assistant_avatar = app_config.get("assistant_avatar", "🐱")

    role = message["role"]
    content = message["content"]
    timestamp = message.get("timestamp", "")

    if role == "system":
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(f"*System: {content}*")
            if timestamp:
                st.caption(f"Time: {timestamp}")
    else:
        avatar = assistant_avatar if role == "assistant" else "👤"
        with st.chat_message(role, avatar=avatar):
            if content.startswith("![Generated Image](http"):
                url = content.split("(")[1].rstrip(")")
                try:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.image(url, caption="Generated Image", width=300)
                        try:
                            response = requests.get(url)
                            if response.status_code == 200:
                                st.download_button(
                                    label="⬇️",
                                    data=response.content,
                                    file_name=f"catgpt_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                                    mime="image/png"
                                )
                        except:
                            pass
                except:
                    st.error("Failed to load image")
                    st.markdown(content)
            else:
                st.markdown(content)

            if timestamp:
                st.caption(f"Time: {timestamp}")


with st.sidebar:
    admin_settings = load_admin_settings()
    app_config = admin_settings.get("app_config", {})
    app_title = app_config.get("app_title", "CatGPT")

    col1, col2 = st.columns([2, 2])
    with col1:
        st.title(app_title)
        if "current_user" in st.session_state and st.session_state.current_user:
            users = load_users()
            user_name = users.get(st.session_state.current_user, {}).get("name", st.session_state.current_user)
            st.caption(f"Welcome, {user_name}")
    with col2:
        if st.button("Logout", use_container_width=True):
            logout()

    st.markdown("---")

    st.subheader("Chat Sessions")

    if st.button("New Chat", use_container_width=True):
        create_new_session()

    if st.button("Save Current", use_container_width=True):
        save_current_session()
        st.success("Session saved!")
        time.sleep(1)

    if st.button("🌐 Global Chat", use_container_width=True):
        st.session_state.show_global_chat = True
        st.rerun()

    if st.session_state.chat_sessions:
        st.write("**Previous Sessions:**")
        for session_id, session in list(st.session_state.chat_sessions.items())[-5:]:
            session_name = session["name"]
            if len(session_name) > 20:
                session_name = session_name[:20] + "..."

            if st.button(f" {session_name}", key=f"load_{session_id}", use_container_width=True):
                load_session(session_id)

    st.markdown("---")
    st.subheader("Chat Statistics")

    current_tokens = get_conversation_token_count(st.session_state.chat_history)
    st.metric("Current Session Messages", len(st.session_state.chat_history))
    st.metric("Current Session Tokens", current_tokens)
    st.metric("Total Messages Sent", st.session_state.message_count)
    st.metric("Total Tokens Used", st.session_state.total_tokens)

    admin_settings = load_admin_settings()
    memory_settings = admin_settings.get("memory_settings", {
        "max_context_messages": 20,
        "max_context_tokens": 4000,
        "summarize_old_context": True,
        "keep_important_messages": True
    })

    if current_tokens > memory_settings["max_context_tokens"] * 0.8:
        st.warning("Approaching token limit")
    elif len(st.session_state.chat_history) > memory_settings["max_context_messages"] * 0.8:
        st.warning("Approaching message limit")

    if "current_user" in st.session_state and st.session_state.current_user:
        can_generate, message = check_image_generation_limit(st.session_state.current_user)
        if can_generate:
            st.success(f" {message}")
        else:
            st.error(f"🚫 {message}")

admin_settings = load_admin_settings()
app_config = admin_settings.get("app_config", {})
app_title = app_config.get("app_title", "CatGPT")

st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1>{app_title}</h1>
    </div>
""", unsafe_allow_html=True)

for message in st.session_state.chat_history:
    display_message(message)

if prompt := st.chat_input("What would you like to know?"):
    user_message = {
        "role": "user",
        "content": prompt,
        "timestamp": format_message_time()
    }
    st.session_state.chat_history.append(user_message)
    st.session_state.message_count += 1

    display_message(user_message)

    if detect_image_request(prompt):
        can_generate, limit_message = check_image_generation_limit(st.session_state.current_user)

        if not can_generate:
            admin_settings = load_admin_settings()
            app_config = admin_settings.get("app_config", {})
            assistant_avatar = app_config.get("assistant_avatar", "🐱")

            with st.chat_message("assistant", avatar=assistant_avatar):
                st.error(limit_message)
                assistant_message = {
                    "role": "assistant",
                    "content": f"I'm sorry, but {limit_message.lower()}. Please contact your administrator if you need to generate more images.",
                    "timestamp": format_message_time()
                }
                st.session_state.chat_history.append(assistant_message)
                save_data_to_file()
        else:
            admin_settings = load_admin_settings()
            app_config = admin_settings.get("app_config", {})
            assistant_avatar = app_config.get("assistant_avatar", "🐱")

            with st.chat_message("assistant", avatar=assistant_avatar):
                with st.spinner("CatGPT is generating your image..."):
                    try:
                        image_url = generate_dalle_image(prompt)
                        increment_image_usage(st.session_state.current_user)

                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.image(image_url, caption="Generated Image", width=300)
                            try:
                                response = requests.get(image_url)
                                if response.status_code == 200:
                                    st.download_button(
                                        label="⬇️",
                                        data=response.content,
                                        file_name=f"catgpt_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                                        mime="image/png"
                                    )
                            except:
                                pass

                        assistant_message = {
                            "role": "assistant",
                            "content": f"![Generated Image]({image_url})",
                            "timestamp": format_message_time()
                        }
                        st.session_state.chat_history.append(assistant_message)

                        save_data_to_file()

                    except Exception as e:
                        st.error(f"Error generating image: {str(e)}")
                        error_message = {
                            "role": "assistant",
                            "content": f"I apologize, but I encountered an error while generating the image: {str(e)}",
                            "timestamp": format_message_time()
                        }
                        st.session_state.chat_history.append(error_message)
                        save_data_to_file()
    else:
        managed_history = manage_conversation_memory(st.session_state.chat_history)

        admin_settings = load_admin_settings()
        app_config = admin_settings.get("app_config", {})
        assistant_avatar = app_config.get("assistant_avatar", "🐱")
        model_name = app_config.get("model_name", "CatGPT")
        system_prompt = admin_settings.get("system_prompt",
                                           f"You are {model_name}, a helpful AI assistant. You have access to our previous conversation history and can reference past messages to provide contextual responses.")

        api_messages = [{"role": "system", "content": system_prompt}]

        for msg in managed_history:
            if msg["role"] != "system" or not msg["content"].startswith("[Previous conversation"):
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        with st.chat_message("assistant", avatar=assistant_avatar):
            with st.spinner(f"{model_name} is thinking..."):
                try:
                    response = openai.chat.completions.create(
                        model=st.session_state.model,
                        messages=api_messages,
                        temperature=0.7,
                        max_tokens=2000,
                        stream=True
                    )

                    response_placeholder = st.empty()
                    full_response = ""

                    for chunk in response:
                        if chunk.choices[0].delta.content is not None:
                            full_response += chunk.choices[0].delta.content
                            response_placeholder.markdown(full_response + "▌")

                    response_placeholder.markdown(full_response)

                    assistant_message = {
                        "role": "assistant",
                        "content": full_response,
                        "timestamp": format_message_time()
                    }
                    st.session_state.chat_history.append(assistant_message)

                    response_tokens = get_token_count(full_response, st.session_state.model)
                    prompt_tokens = get_token_count(prompt, st.session_state.model)
                    st.session_state.total_tokens += response_tokens + prompt_tokens

                    save_data_to_file()

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    error_message = {
                        "role": "system",
                        "content": f"Error occurred: {str(e)}",
                        "timestamp": format_message_time()
                    }
                    st.session_state.chat_history.append(error_message)
                    save_data_to_file()

if len(st.session_state.chat_history) > 0:
    save_data_to_file()

admin_settings = load_admin_settings()
app_config = admin_settings.get("app_config", {})
app_title = app_config.get("app_title", "CatGPT")

st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; font-size: 0.8rem;'>
    {app_title} v7.0 - Your AI Assistant with Memory<br>
    Built by Shuvo | 2025
</div>
""", unsafe_allow_html=True)