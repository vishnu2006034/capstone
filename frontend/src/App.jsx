import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  LayoutDashboard,
  Video,
  CheckSquare,
  BookOpen,
  ShieldCheck,
  BarChart3,
  Bot,
  LogOut,
  Bell,
  Plus,
  Trash2,
  Calendar,
  AlertTriangle,
  UserPlus,
  Send,
  Loader2,
  Lock,
  Mail,
  User as UserIcon,
  ChevronRight,
  Upload,
  MessageSquare,
  Clock,
  CheckCircle2,
  XCircle,
  HelpCircle
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export default function App() {
  // Authentication State
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('user')) || null);
  const [isRegistering, setIsRegistering] = useState(false);
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '', role: 'Employee' });

  // Navigation State
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Dashboard & Metrics State
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [stats, setStats] = useState({ meetings: 0, activeTasks: 0, triageTasks: 0, sops: 0 });

  // Core Data Lists
  const [meetings, setMeetings] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [sops, setSops] = useState([]);
  const [complianceReports, setComplianceReports] = useState([]);
  const [users, setUsers] = useState([]); // for assignment dropdowns

  // Filter States
  const [taskFilter, setTaskFilter] = useState({ priority: '', status: '', search: '', assignee: '' });
  const [sopSearch, setSopSearch] = useState('');

  // Selected Detail Elements
  const [selectedTask, setSelectedTask] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [selectedSop, setSelectedSop] = useState(null);
  
  // Forms & Modal State
  const [showMeetingModal, setShowMeetingModal] = useState(false);
  const [newMeetingTitle, setNewMeetingTitle] = useState('');
  const [newTranscript, setNewTranscript] = useState('');
  const [showSopModal, setShowSopModal] = useState(false);
  const [newSop, setNewSop] = useState({ title: '', department: 'Engineering', version: '1.0.0' });
  const [newSopSections, setNewSopSections] = useState([{ section_number: '1.1', title: 'Purpose', content: '' }]);
  const [isProcessingMIA, setIsProcessingMIA] = useState({});

  // Manager Copilot State
  const [copilotQuery, setCopilotQuery] = useState('');
  const [copilotAnswer, setCopilotAnswer] = useState('');
  const [copilotLoading, setCopilotLoading] = useState(false);

  // Global Axios Auth Configuration
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      fetchGlobalData();
    } else {
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
  }, [token]);

  // Fetch data periodically
  useEffect(() => {
    if (token) {
      const interval = setInterval(() => {
        fetchNotifications();
      }, 10000);
      return () => clearInterval(interval);
    }
  }, [token]);

  const fetchGlobalData = async () => {
    try {
      fetchNotifications();
      fetchMeetings();
      fetchTasks();
      fetchSops();
      fetchComplianceReports();
      fetchUsers();
    } catch (e) {
      console.error('Error loading global system data', e);
    }
  };

  // --- API CALLS ---
  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);
    try {
      const resp = await axios.post(`${API_BASE}/auth/login`, {
        email: authForm.email,
        password: authForm.password
      });
      setToken(resp.data.access_token);
      // Fetch self profile
      const profile = await axios.get(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${resp.data.access_token}` }
      });
      setUser(profile.data);
    } catch (err) {
      setAuthError(err.response?.data?.error?.message || 'Login failed. Verify credentials.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);
    try {
      await axios.post(`${API_BASE}/auth/register`, authForm);
      setIsRegistering(false);
      setAuthForm({ name: '', email: '', password: '', role: 'Employee' });
      alert('Registration successful! Please login.');
    } catch (err) {
      setAuthError(err.response?.data?.error?.message || 'Registration failed.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    setToken('');
    setUser(null);
    setActiveTab('dashboard');
  };

  const fetchNotifications = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/notifications`);
      setNotifications(resp.data);
    } catch (err) {
      console.error('Error fetching notifications', err);
    }
  };

  const markNotificationRead = async (id) => {
    try {
      await axios.post(`${API_BASE}/notifications/${id}/read`);
      setNotifications(prev => prev.filter(n => n.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  const fetchMeetings = async () => {
    const resp = await axios.get(`${API_BASE}/meetings`);
    setMeetings(resp.data);
  };

  const fetchTasks = async () => {
    let url = `${API_BASE}/tasks?`;
    if (taskFilter.status) url += `status=${taskFilter.status}&`;
    if (taskFilter.priority) url += `priority=${taskFilter.priority}&`;
    if (taskFilter.search) url += `search=${taskFilter.search}&`;
    if (taskFilter.assignee) url += `assignee_id=${taskFilter.assignee}&`;
    const resp = await axios.get(url);
    setTasks(resp.data);
  };

  const fetchSops = async () => {
    let url = `${API_BASE}/sops`;
    if (sopSearch) url += `?search=${sopSearch}`;
    const resp = await axios.get(url);
    setSops(resp.data);
  };

  const fetchComplianceReports = async () => {
    // Collect all tasks and aggregate their compliance reports
    const resp = await axios.get(`${API_BASE}/tasks`);
    const reports = [];
    resp.data.forEach(task => {
      if (task.comments) {
        // Fetch compliance reports from backend tasks
      }
    });
    // We can also query all reports from database (list endpoints in backend)
    // For simplicity, we get reports from detailed task objects
    const detailedTasks = await Promise.all(resp.data.slice(0, 10).map(t => axios.get(`${API_BASE}/tasks/${t.id}`)));
    const allReports = [];
    detailedTasks.forEach(r => {
      // In mock/test databases, we query task detail containing compliance_reports
      // To satisfy dashboard compliance tabs, we map reports:
    });
  };

  const fetchUsers = async () => {
    // In auth endpoints, register users can be fetched, or we mock assignees
    // Typically, user list is fetched via a directory API
    setUsers([
      { id: '1', name: 'Alice Developer', email: 'alice.dev@company.com', role: 'Employee' },
      { id: '2', name: 'Bob Engineer', email: 'bob@company.com', role: 'Employee' },
      { id: '3', name: 'PM Manager', email: 'manager@company.com', role: 'Manager' },
      { id: '4', name: 'Jane Auditor', email: 'compliance@company.com', role: 'Compliance Officer' }
    ]);
  };

  // Run periodic metrics update
  useEffect(() => {
    if (meetings.length || tasks.length) {
      const active = tasks.filter(t => t.status !== 'Done').length;
      const triage = tasks.filter(t => t.status === 'Triage').length;
      setStats({
        meetings: meetings.length,
        activeTasks: active,
        triageTasks: triage,
        sops: sops.length
      });
    }
  }, [meetings, tasks, sops]);

  useEffect(() => {
    if (token) fetchTasks();
  }, [taskFilter]);

  const createMeeting = async () => {
    if (!newMeetingTitle) return;
    try {
      const resp = await axios.post(`${API_BASE}/meetings`, { title: newMeetingTitle });
      if (newTranscript) {
        await axios.post(`${API_BASE}/meetings/${resp.data.id}/upload-transcript`, { raw_text: newTranscript });
      }
      setShowMeetingModal(false);
      setNewMeetingTitle('');
      setNewTranscript('');
      fetchMeetings();
    } catch (err) {
      alert('Error creating meeting: ' + err.message);
    }
  };

  const deleteMeeting = async (id) => {
    if (!window.confirm('Delete meeting and all generated tasks?')) return;
    await axios.delete(`${API_BASE}/meetings/${id}`);
    fetchMeetings();
    fetchTasks();
  };

  const triggerMIA = async (id) => {
    setIsProcessingMIA(prev => ({ ...prev, [id]: true }));
    try {
      // BackgroundTasks triggers MEETING_UPLOADED trigger
      // To simulate MIA extract immediately:
      // In production, uploading raw transcript triggers it. We can re-upload to trigger.
      const meeting = meetings.find(m => m.id === id);
      await axios.post(`${API_BASE}/meetings/${id}/upload-transcript`, { raw_text: meeting.transcript?.raw_text || 'Mock dialog' });
      alert('Meeting Intelligence Agent triggered. Check dashboard for generated tasks.');
      fetchMeetings();
      fetchTasks();
    } catch (err) {
      alert(err.message);
    } finally {
      setIsProcessingMIA(prev => ({ ...prev, [id]: false }));
    }
  };

  const loadTaskComments = async (taskId) => {
    const resp = await axios.get(`${API_BASE}/tasks/${taskId}`);
    setSelectedTask(resp.data);
    setComments(resp.data.comments || []);
  };

  const postComment = async () => {
    if (!newComment || !selectedTask) return;
    const resp = await axios.post(`${API_BASE}/tasks/${selectedTask.id}/comments`, { content: newComment });
    setComments(prev => [...prev, resp.data]);
    setNewComment('');
    // refresh task details
    loadTaskComments(selectedTask.id);
  };

  const updateTaskStatus = async (taskId, nextStatus) => {
    await axios.put(`${API_BASE}/tasks/${taskId}`, { status: nextStatus });
    fetchTasks();
    if (selectedTask?.id === taskId) {
      loadTaskComments(taskId);
    }
  };

  const assignTask = async (taskId, email) => {
    await axios.post(`${API_BASE}/tasks/${taskId}/assign`, { emails: [email] });
    fetchTasks();
    if (selectedTask?.id === taskId) {
      loadTaskComments(taskId);
    }
  };

  const createSop = async () => {
    try {
      const payload = {
        title: newSop.title,
        department: newSop.department,
        version: newSop.version,
        sections: newSopSections.filter(s => s.content)
      };
      await axios.post(`${API_BASE}/sops`, payload);
      setShowSopModal(false);
      setNewSop({ title: '', department: 'Engineering', version: '1.0.0' });
      setNewSopSections([{ section_number: '1.1', title: 'Purpose', content: '' }]);
      fetchSops();
    } catch (err) {
      alert(err.response?.data?.error?.message || err.message);
    }
  };

  const deleteSop = async (id) => {
    if (!window.confirm('Delete SOP policy document?')) return;
    await axios.delete(`${API_BASE}/sops/${id}`);
    fetchSops();
  };

  const runCopilotQuery = async (prebuilt = '') => {
    const q = prebuilt || copilotQuery;
    if (!q) return;
    setCopilotLoading(true);
    try {
      const resp = await axios.post(`${API_BASE}/copilot/query`, { query: q });
      setCopilotAnswer(resp.data.answer);
    } catch (err) {
      setCopilotAnswer('Error consulting Copilot: ' + (err.response?.data?.error?.message || err.message));
    } finally {
      setCopilotLoading(false);
    }
  };

  const triggerAuditRun = async () => {
    try {
      await axios.post(`${API_BASE}/notifications/trigger-escalations`);
      alert('Auditor scan run completed. Notifications generated for overdue metrics.');
      fetchNotifications();
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Access Denied: Managers and Admins only.');
    }
  };

  // Analytics Helpers
  const getWorkloadData = () => {
    // Count incomplete tasks assigned to each email
    const workload = {};
    tasks.forEach(t => {
      if (t.status !== 'Done') {
        t.assignees?.forEach(a => {
          workload[a.name] = (workload[a.name] || 0) + 1;
        });
      }
    });
    return Object.keys(workload).map(name => ({ name, tasks: workload[name] }));
  };

  const getMeetingTaskData = () => {
    const meetingCounts = {};
    tasks.forEach(t => {
      const mTitle = t.meeting_title || 'Direct Creation';
      meetingCounts[mTitle] = (meetingCounts[mTitle] || 0) + 1;
    });
    const COLORS = ['#8b5cf6', '#a855f7', '#c084fc', '#3b82f6', '#10b981', '#f59e0b'];
    return Object.keys(meetingCounts).map((title, i) => ({
      name: title,
      value: meetingCounts[title],
      color: COLORS[i % COLORS.length]
    }));
  };

  // Render Auth UI if not logged in
  if (!token) {
    return (
      <div className="min-height-screen bg-dark-950 flex items-center justify-center p-4 relative overflow-hidden">
        {/* Neon Gradient Blobs */}
        <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-brand-900/20 blur-[120px] pointer-events-none"></div>
        <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-brand-500/10 blur-[120px] pointer-events-none"></div>

        <div className="w-full max-w-md bg-dark-900/80 border border-dark-800 rounded-2xl shadow-2xl backdrop-blur-xl p-8 transition-all duration-300">
          <div className="flex flex-col items-center mb-8">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center shadow-lg shadow-brand-500/20 mb-3">
              <Bot className="h-7 w-7 text-white" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Meeting2Execution AI</h1>
            <p className="text-sm text-dark-400 mt-1">Multi-Agent Operations & SOP Compliance Hub</p>
          </div>

          <form onSubmit={isRegistering ? handleRegister : handleLogin} className="space-y-5">
            {isRegistering && (
              <div>
                <label className="text-xs font-semibold uppercase text-dark-400 block mb-2">Full Name</label>
                <div className="relative">
                  <UserIcon className="absolute left-3 top-3.5 h-5 w-5 text-dark-500" />
                  <input
                    type="text"
                    required
                    placeholder="Jane Doe"
                    value={authForm.name}
                    onChange={e => setAuthForm({ ...authForm, name: e.target.value })}
                    className="w-full bg-dark-950 border border-dark-800 rounded-xl py-3 pl-11 pr-4 text-white placeholder-dark-600 focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 transition-all text-sm"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="text-xs font-semibold uppercase text-dark-400 block mb-2">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-3.5 h-5 w-5 text-dark-500" />
                <input
                  type="email"
                  required
                  placeholder="jane@company.com"
                  value={authForm.email}
                  onChange={e => setAuthForm({ ...authForm, email: e.target.value })}
                  className="w-full bg-dark-950 border border-dark-800 rounded-xl py-3 pl-11 pr-4 text-white placeholder-dark-600 focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 transition-all text-sm"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase text-dark-400 block mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-3.5 h-5 w-5 text-dark-500" />
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={authForm.password}
                  onChange={e => setAuthForm({ ...authForm, password: e.target.value })}
                  className="w-full bg-dark-950 border border-dark-800 rounded-xl py-3 pl-11 pr-4 text-white placeholder-dark-600 focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 transition-all text-sm"
                />
              </div>
            </div>

            {isRegistering && (
              <div>
                <label className="text-xs font-semibold uppercase text-dark-400 block mb-2">Corporate Role</label>
                <select
                  value={authForm.role}
                  onChange={e => setAuthForm({ ...authForm, role: e.target.value })}
                  className="w-full bg-dark-950 border border-dark-800 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-brand-500 transition-all text-sm"
                >
                  <option value="Employee">Employee</option>
                  <option value="Manager">Manager</option>
                  <option value="Compliance Officer">Compliance Officer</option>
                  <option value="Admin">Admin</option>
                </select>
              </div>
            )}

            {authError && (
              <div className="bg-red-950/30 border border-red-800/40 text-red-400 text-xs rounded-xl p-3 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="w-full bg-brand-600 hover:bg-brand-500 disabled:bg-brand-800 text-white rounded-xl py-3 text-sm font-semibold flex items-center justify-center gap-2 transition-all duration-200 shadow-lg shadow-brand-600/10 hover:shadow-brand-600/20"
            >
              {authLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {isRegistering ? 'Register Profile' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-dark-400">
            {isRegistering ? (
              <p>Already have an account? <button onClick={() => setIsRegistering(false)} className="text-brand-400 hover:underline">Sign In</button></p>
            ) : (
              <p>Need corporate access? <button onClick={() => setIsRegistering(true)} className="text-brand-400 hover:underline">Request Account</button></p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Main UI
  return (
    <div className="min-h-screen bg-dark-950 flex flex-col md:flex-row relative">
      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 bg-dark-900 border-r border-dark-800 flex flex-col shrink-0">
        {/* Brand */}
        <div className="p-6 border-b border-dark-800 flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center shadow-lg">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-white text-sm tracking-tight leading-tight">M2E Intelligence</h2>
            <span className="text-[10px] text-dark-500 font-medium uppercase tracking-wider">Active Workspace</span>
          </div>
        </div>

        {/* User Card */}
        <div className="p-4 mx-4 my-3 bg-dark-950/60 border border-dark-800/80 rounded-xl flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-brand-900/30 flex items-center justify-center text-brand-400 font-bold border border-brand-800/40">
            {user?.name?.[0]?.toUpperCase()}
          </div>
          <div className="overflow-hidden">
            <h4 className="text-xs font-semibold text-white truncate">{user?.name}</h4>
            <span className="text-[10px] text-brand-400 bg-brand-950/50 border border-brand-900/30 px-1.5 py-0.5 rounded font-semibold uppercase">{user?.role}</span>
          </div>
        </div>

        {/* Menu Tabs */}
        <nav className="flex-1 px-4 space-y-1 py-3">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
            { id: 'meetings', label: 'Meetings', icon: Video },
            { id: 'tasks', label: 'Tasks Desk', icon: CheckSquare },
            { id: 'sops', label: 'SOP Library', icon: BookOpen },
            { id: 'compliance', label: 'Compliance Panel', icon: ShieldCheck },
            { id: 'analytics', label: 'Metrics Analytics', icon: BarChart3 },
            { id: 'copilot', label: 'Manager Copilot', icon: Bot, roles: ['Admin', 'Manager'] }
          ].map(tab => {
            if (tab.roles && !tab.roles.includes(user?.role)) return null;
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => { setActiveTab(tab.id); setSelectedTask(null); }}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                  activeTab === tab.id
                    ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/10'
                    : 'text-dark-400 hover:bg-dark-800/60 hover:text-white'
                }`}
              >
                <Icon className="h-4.5 w-4.5 shrink-0" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="p-4 border-t border-dark-800">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium text-red-400 hover:bg-red-950/20 transition-all"
          >
            <LogOut className="h-4.5 w-4.5 shrink-0" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Panel Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Header bar */}
        <header className="h-16 bg-dark-900 border-b border-dark-800 flex items-center justify-between px-6 shrink-0 relative z-30">
          <h2 className="text-sm font-bold text-white capitalize">{activeTab} Panel</h2>

          {/* Alert Hub */}
          <div className="flex items-center gap-4 relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="relative p-2 rounded-full hover:bg-dark-800 text-dark-400 hover:text-white transition-all"
            >
              <Bell className="h-5 w-5" />
              {notifications.length > 0 && (
                <span className="absolute top-1 right-1 h-4 w-4 bg-brand-500 text-[9px] font-bold text-white rounded-full flex items-center justify-center animate-pulse">
                  {notifications.length}
                </span>
              )}
            </button>

            {showNotifications && (
              <div className="absolute right-0 top-12 w-80 bg-dark-900 border border-dark-800 rounded-xl shadow-2xl z-50 p-4 transition-all animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center justify-between mb-3 border-b border-dark-850 pb-2">
                  <h4 className="text-xs font-bold text-white">Dashboard Alerts</h4>
                  <span className="text-[10px] text-brand-400 font-semibold">{notifications.length} Unread</span>
                </div>

                <div className="max-h-64 overflow-y-auto space-y-3">
                  {notifications.length === 0 ? (
                    <p className="text-center text-dark-500 py-6 text-xs">No alerts. All clear!</p>
                  ) : (
                    notifications.map(n => (
                      <div key={n.id} className="p-2.5 bg-dark-950 border border-dark-800 rounded-lg flex items-start justify-between gap-2">
                        <div>
                          <h5 className="text-xs font-semibold text-white">{n.title}</h5>
                          <p className="text-[10px] text-dark-400 mt-1">{n.content}</p>
                        </div>
                        <button
                          onClick={() => markNotificationRead(n.id)}
                          className="text-[9px] bg-brand-950 text-brand-400 border border-brand-900/30 px-1.5 py-0.5 rounded font-semibold hover:bg-brand-900/20"
                        >
                          Clear
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Content Body Panels */}
        <div className="flex-1 p-6 relative">
          
          {/* TAB: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              {/* Leader Audit Alert Trigger Bar */}
              {['Admin', 'Manager'].includes(user?.role) && (
                <div className="p-4 bg-gradient-to-r from-brand-900/30 to-dark-900 border border-brand-900/30 rounded-xl flex items-center justify-between flex-wrap gap-4 shadow-lg shadow-brand-900/5">
                  <div>
                    <h4 className="text-xs font-bold text-white">Operations Compliance Scan</h4>
                    <p className="text-[10px] text-dark-400 mt-0.5">Scan database records, check overdue actions, and send alerts.</p>
                  </div>
                  <button
                    onClick={triggerAuditRun}
                    className="bg-brand-600 hover:bg-brand-500 text-white text-xs px-4 py-2 rounded-lg font-semibold flex items-center gap-2 transition-all"
                  >
                    <ShieldCheck className="h-4 w-4" />
                    Run Auditor Scan
                  </button>
                </div>
              )}

              {/* Status Metrics Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: 'Total Meetings', val: stats.meetings, color: 'text-purple-450', desc: 'Ingested transcript logs' },
                  { label: 'Active Task Items', val: stats.activeTasks, color: 'text-blue-400', desc: 'Outstanding items' },
                  { label: 'Audited Triages', val: stats.triageTasks, color: 'text-amber-400', desc: 'Blocked compliance items' },
                  { label: 'Registered SOPs', val: stats.sops, color: 'text-emerald-400', desc: 'Department procedures' }
                ].map((card, i) => (
                  <div key={i} className="bg-dark-900 border border-dark-800 p-5 rounded-xl flex items-center justify-between">
                    <div>
                      <span className="text-xs font-medium text-dark-400">{card.label}</span>
                      <h3 className={`text-2xl font-bold ${card.color} mt-1.5`}>{card.val}</h3>
                      <p className="text-[10px] text-dark-500 mt-1">{card.desc}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Grid: Actions & Overdue items */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left: General Info */}
                <div className="lg:col-span-2 bg-dark-900 border border-dark-800 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4 pb-2 border-b border-dark-800">
                    <h3 className="text-xs font-bold text-white">Recent Work Activity</h3>
                  </div>
                  <div className="space-y-3 max-h-80 overflow-y-auto">
                    {tasks.slice(0, 5).map(task => (
                      <div key={task.id} className="p-3 bg-dark-950 border border-dark-800/80 rounded-lg flex items-center justify-between gap-4">
                        <div>
                          <h4 className="text-xs font-semibold text-white">{task.title}</h4>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[9px] text-dark-400">Meeting: {task.meeting_title || 'Planning'}</span>
                            <span className="text-[9px] text-dark-500">•</span>
                            <span className="text-[9px] text-dark-400">Status: {task.status}</span>
                          </div>
                        </div>
                        <span className={`text-[9px] px-2 py-0.5 rounded font-semibold uppercase ${
                          task.priority === 'CRITICAL' ? 'bg-red-950/50 text-red-400 border border-red-900/40' :
                          task.priority === 'HIGH' ? 'bg-amber-950/50 text-amber-400 border border-amber-900/40' :
                          'bg-dark-800 text-dark-400 border border-dark-700'
                        }`}>
                          {task.priority}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Right: Quick Ingest */}
                <div className="bg-dark-900 border border-dark-800 rounded-xl p-5 flex flex-col justify-between">
                  <div>
                    <h3 className="text-xs font-bold text-white mb-2">Ingest Meeting Transcript</h3>
                    <p className="text-[10px] text-dark-400 mb-4">Ingest meeting minutes to auto-extract tasks and verify compliance.</p>
                  </div>
                  <button
                    onClick={() => setShowMeetingModal(true)}
                    className="w-full bg-brand-600 hover:bg-brand-500 text-white rounded-lg py-2.5 text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                  >
                    <Plus className="h-4 w-4" />
                    New Meeting Transcript
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB: MEETINGS */}
          {activeTab === 'meetings' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-white uppercase">Ingested Meetings</h3>
                <button
                  onClick={() => setShowMeetingModal(true)}
                  className="bg-brand-600 hover:bg-brand-500 text-white text-xs px-3.5 py-2 rounded-lg font-semibold flex items-center gap-1.5 transition-all"
                >
                  <Plus className="h-4 w-4" />
                  New Transcript
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {meetings.length === 0 ? (
                  <div className="col-span-full bg-dark-900 border border-dark-800 rounded-xl p-12 text-center text-dark-400">
                    <Video className="h-10 w-10 text-dark-600 mx-auto mb-2" />
                    <p className="text-xs">No meetings ingested. Get started by uploading a transcript.</p>
                  </div>
                ) : (
                  meetings.map(meeting => (
                    <div key={meeting.id} className="bg-dark-900 border border-dark-800 rounded-xl p-5 flex flex-col justify-between hover:border-brand-500/30 transition-all duration-150">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase ${
                            meeting.status === 'Extracted' ? 'bg-emerald-950/50 text-emerald-400 border border-emerald-900/30' :
                            meeting.status === 'Transcribed' ? 'bg-blue-950/50 text-blue-400 border border-blue-900/30' :
                            'bg-dark-850 text-dark-500 border border-dark-800'
                          }`}>
                            {meeting.status}
                          </span>
                          <button
                            onClick={() => deleteMeeting(meeting.id)}
                            className="text-dark-500 hover:text-red-400 p-1 hover:bg-dark-850 rounded transition-all"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                        <h4 className="text-xs font-bold text-white leading-tight mb-3">{meeting.title}</h4>
                        <div className="flex items-center gap-1.5 text-[10px] text-dark-500 mb-4">
                          <Calendar className="h-3.5 w-3.5" />
                          <span>{new Date(meeting.scheduled_time || meeting.created_at).toLocaleString()}</span>
                        </div>
                      </div>

                      <button
                        onClick={() => triggerMIA(meeting.id)}
                        disabled={isProcessingMIA[meeting.id]}
                        className="w-full bg-dark-950 border border-brand-900/40 hover:bg-brand-950/60 disabled:bg-dark-900 text-brand-400 text-xs font-semibold py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all border-dashed"
                      >
                        {isProcessingMIA[meeting.id] ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                        {isProcessingMIA[meeting.id] ? 'Extracting Tasks...' : 'Trigger MIA Agent'}
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB: TASKS DESK */}
          {activeTab === 'tasks' && (
            <div className="space-y-4">
              {/* Task filters */}
              <div className="bg-dark-900 border border-dark-800 p-4 rounded-xl flex flex-wrap items-center gap-3">
                <input
                  type="text"
                  placeholder="Search tasks..."
                  value={taskFilter.search}
                  onChange={e => setTaskFilter({ ...taskFilter, search: e.target.value })}
                  className="bg-dark-950 border border-dark-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-dark-600 focus:outline-none focus:border-brand-500"
                />

                <select
                  value={taskFilter.status}
                  onChange={e => setTaskFilter({ ...taskFilter, status: e.target.value })}
                  className="bg-dark-950 border border-dark-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none"
                >
                  <option value="">All Statuses</option>
                  <option value="Extracted">Extracted</option>
                  <option value="Approved">Approved</option>
                  <option value="Triage">Triage</option>
                  <option value="InProgress">InProgress</option>
                  <option value="Done">Done</option>
                </select>

                <select
                  value={taskFilter.priority}
                  onChange={e => setTaskFilter({ ...taskFilter, priority: e.target.value })}
                  className="bg-dark-950 border border-dark-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none"
                >
                  <option value="">All Priorities</option>
                  <option value="LOW">LOW</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="HIGH">HIGH</option>
                  <option value="CRITICAL">CRITICAL</option>
                </select>
              </div>

              {/* Tasks Layout container */}
              <div className="flex flex-col lg:flex-row gap-6 items-start">
                <div className="flex-1 min-w-0 space-y-3">
                  {tasks.length === 0 ? (
                    <div className="bg-dark-900 border border-dark-800 rounded-xl p-12 text-center text-dark-400">
                      <CheckSquare className="h-10 w-10 text-dark-600 mx-auto mb-2" />
                      <p className="text-xs">No tasks match selected filter criteria.</p>
                    </div>
                  ) : (
                    tasks.map(task => (
                      <div
                        key={task.id}
                        onClick={() => loadTaskComments(task.id)}
                        className={`p-4 bg-dark-900 border rounded-xl flex items-center justify-between gap-4 hover:border-brand-500/20 cursor-pointer transition-all ${
                          selectedTask?.id === task.id ? 'border-brand-500 bg-brand-950/10' : 'border-dark-800'
                        }`}
                      >
                        <div className="overflow-hidden">
                          <h4 className="text-xs font-bold text-white truncate">{task.title}</h4>
                          <p className="text-[10px] text-dark-400 truncate mt-1">
                            {task.description?.replace(/\*\*Risks Identified:\*\*/g, '') || 'No description'}
                          </p>
                          <div className="flex items-center gap-2 mt-2">
                            <span className="text-[9px] text-dark-500">Status: {task.status}</span>
                            <span className="text-[9px] text-dark-500">•</span>
                            <span className="text-[9px] text-dark-500">Assignees: {task.assignees?.map(a => a.name).join(', ') || 'Unassigned'}</span>
                          </div>
                        </div>

                        <span className={`text-[9px] px-2 py-0.5 rounded font-semibold uppercase shrink-0 ${
                          task.priority === 'CRITICAL' ? 'bg-red-950/50 text-red-400 border border-red-900/40' :
                          task.priority === 'HIGH' ? 'bg-amber-950/50 text-amber-400 border border-amber-900/40' :
                          'bg-dark-850 text-dark-400 border border-dark-750'
                        }`}>
                          {task.priority}
                        </span>
                      </div>
                    ))
                  )}
                </div>

                {/* Right: Comments / Details Sidebar Drawer */}
                {selectedTask && (
                  <div className="w-full lg:w-96 shrink-0 bg-dark-900 border border-dark-800 rounded-xl p-5 space-y-5 sticky top-6">
                    <div className="border-b border-dark-800 pb-3">
                      <h3 className="text-xs font-bold text-white">{selectedTask.title}</h3>
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        <select
                          value={selectedTask.status}
                          onChange={e => updateTaskStatus(selectedTask.id, e.target.value)}
                          className="bg-dark-950 border border-dark-800 text-[10px] text-white px-2 py-1 rounded"
                        >
                          <option value="Extracted">Extracted</option>
                          <option value="Approved">Approved</option>
                          <option value="Triage">Triage</option>
                          <option value="InProgress">InProgress</option>
                          <option value="Done">Done</option>
                        </select>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-dark-500">Description / Scope</span>
                        <p className="text-xs text-dark-300 mt-1 whitespace-pre-wrap">{selectedTask.description || 'No description provided.'}</p>
                      </div>

                      {selectedTask.due_date && (
                        <div>
                          <span className="text-[10px] uppercase font-bold text-dark-500">Deadline</span>
                          <div className="text-xs text-dark-300 mt-1 flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5 text-brand-400" />
                            <span>{new Date(selectedTask.due_date).toLocaleString()}</span>
                          </div>
                        </div>
                      )}

                      {/* Assign Developer */}
                      <div>
                        <span className="text-[10px] uppercase font-bold text-dark-500 block mb-1">Assign User</span>
                        <select
                          onChange={e => { if (e.target.value) assignTask(selectedTask.id, e.target.value); }}
                          className="w-full bg-dark-950 border border-dark-800 rounded px-2 py-1 text-xs text-white focus:outline-none"
                        >
                          <option value="">Select Assignee...</option>
                          {users.map(u => (
                            <option key={u.id} value={u.email}>{u.name} ({u.role})</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Comments section */}
                    <div className="border-t border-dark-800 pt-4">
                      <span className="text-[10px] uppercase font-bold text-dark-500 block mb-3">Task Comments</span>
                      <div className="space-y-3 max-h-48 overflow-y-auto mb-3">
                        {comments.length === 0 ? (
                          <p className="text-[10px] text-dark-500 italic py-2">No comments added yet.</p>
                        ) : (
                          comments.map(c => (
                            <div key={c.id} className="p-2 bg-dark-950 border border-dark-800/80 rounded-lg text-xs">
                              <p className="text-dark-300">{c.content}</p>
                              <span className="text-[9px] text-dark-500 block text-right mt-1">{new Date(c.created_at).toLocaleString()}</span>
                            </div>
                          ))
                        )}
                      </div>

                      <div className="flex gap-2">
                        <input
                          type="text"
                          placeholder="Type comment..."
                          value={newComment}
                          onChange={e => setNewComment(e.target.value)}
                          className="flex-1 bg-dark-950 border border-dark-800 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-dark-600 focus:outline-none"
                        />
                        <button
                          onClick={postComment}
                          className="bg-brand-600 hover:bg-brand-500 p-2 rounded-lg text-white"
                        >
                          <Send className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB: SOP LIBRARY */}
          {activeTab === 'sops' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-white uppercase">Procedural SOPs</h3>
                <button
                  onClick={() => setShowSopModal(true)}
                  className="bg-brand-600 hover:bg-brand-500 text-white text-xs px-3.5 py-2 rounded-lg font-semibold flex items-center gap-1.5 transition-all"
                >
                  <Plus className="h-4 w-4" />
                  Upload SOP
                </button>
              </div>

              <div className="bg-dark-900 border border-dark-800 p-4 rounded-xl">
                <input
                  type="text"
                  placeholder="Search SOP documents..."
                  value={sopSearch}
                  onChange={e => setSopSearch(e.target.value)}
                  onKeyUp={e => { if (e.key === 'Enter') fetchSops(); }}
                  className="w-full bg-dark-950 border border-dark-800 rounded-lg px-3 py-2 text-xs text-white placeholder-dark-600 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sops.length === 0 ? (
                  <div className="col-span-full bg-dark-900 border border-dark-800 rounded-xl p-12 text-center text-dark-400">
                    <BookOpen className="h-10 w-10 text-dark-600 mx-auto mb-2" />
                    <p className="text-xs">No SOPs ingested. Register guidelines to start compliance audits.</p>
                  </div>
                ) : (
                  sops.map(sop => (
                    <div
                      key={sop.id}
                      onClick={() => setSelectedSop(sop)}
                      className={`bg-dark-900 border rounded-xl p-5 flex flex-col justify-between hover:border-brand-500/20 cursor-pointer transition-all ${
                        selectedSop?.id === sop.id ? 'border-brand-500 bg-brand-950/5' : 'border-dark-800'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-[9px] bg-brand-950 text-brand-400 border border-brand-900/30 px-1.5 py-0.5 rounded font-semibold uppercase">{sop.department || 'General'}</span>
                          <button
                            onClick={e => { e.stopPropagation(); deleteSop(sop.id); }}
                            className="text-dark-500 hover:text-red-400 p-1 rounded"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                        <h4 className="text-xs font-bold text-white leading-tight mb-2">{sop.title}</h4>
                        <div className="flex items-center justify-between text-[10px] text-dark-500">
                          <span>Version: {sop.version}</span>
                          <span>{new Date(sop.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* SOP Detail section */}
              {selectedSop && (
                <div className="bg-dark-900 border border-dark-800 rounded-xl p-5 space-y-4">
                  <div className="border-b border-dark-800 pb-3 flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-white">{selectedSop.title}</h3>
                      <p className="text-[10px] text-dark-500 mt-1">Department: {selectedSop.department} | Version: {selectedSop.version}</p>
                    </div>
                    <button onClick={() => setSelectedSop(null)} className="text-xs text-dark-400 hover:text-white">Close Details</button>
                  </div>

                  <div className="space-y-4">
                    {/* List sections */}
                    {sops.find(s => s.id === selectedSop.id)?.sections?.map((sec, i) => (
                      <div key={i} className="p-3 bg-dark-950 border border-dark-850 rounded-lg">
                        <h5 className="text-xs font-bold text-white">{sec.section_number} {sec.title}</h5>
                        <p className="text-xs text-dark-300 mt-1.5 whitespace-pre-wrap">{sec.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB: COMPLIANCE PANEL */}
          {activeTab === 'compliance' && (
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-white uppercase mb-2">Compliance Audits</h3>

              <div className="space-y-4">
                {tasks.filter(t => t.compliance_reports && t.compliance_reports.length > 0).length === 0 ? (
                  <div className="bg-dark-900 border border-dark-800 rounded-xl p-12 text-center text-dark-400">
                    <ShieldCheck className="h-10 w-10 text-dark-600 mx-auto mb-2" />
                    <p className="text-xs">No compliance audits run yet. Extract tasks and run scans to generate audit logs.</p>
                  </div>
                ) : (
                  tasks.filter(t => t.compliance_reports && t.compliance_reports.length > 0).map(task => {
                    const report = task.compliance_reports[task.compliance_reports.length - 1];
                    return (
                      <div key={task.id} className="p-5 bg-dark-900 border border-dark-850 rounded-xl space-y-4">
                        <div className="flex items-center justify-between flex-wrap gap-2 border-b border-dark-800 pb-3">
                          <div>
                            <h4 className="text-xs font-bold text-white">Task: {task.title}</h4>
                            <span className="text-[10px] text-dark-400 mt-0.5">Overall grading evaluation</span>
                          </div>
                          
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                              report.status === 'PASSED' ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-900/40' :
                              report.status === 'WARNING' ? 'bg-amber-950/60 text-amber-400 border border-amber-900/40' :
                              'bg-red-950/60 text-red-400 border border-red-900/40'
                            }`}>
                              {report.status}
                            </span>
                            <span className="text-[10px] bg-dark-950 border border-dark-800 px-2 py-0.5 rounded text-white font-semibold">
                              Score: {report.compliance_score}/100
                            </span>
                          </div>
                        </div>

                        {/* Checklist Details */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <h5 className="text-[10px] uppercase font-bold text-dark-500 mb-2">Audit Check Items</h5>
                            <div className="space-y-1.5">
                              {report.checklist?.map((item, index) => (
                                <div key={index} className="flex items-center gap-2 text-xs">
                                  {item.passed ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <XCircle className="h-4 w-4 text-red-400" />}
                                  <span className={item.passed ? 'text-dark-300' : 'text-red-400/80'}>{item.item}</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div>
                            <h5 className="text-[10px] uppercase font-bold text-dark-500 mb-2">Missing procedural steps</h5>
                            <div className="space-y-1 bg-dark-950 p-3 border border-dark-850 rounded-lg">
                              {report.missing_steps?.length === 0 ? (
                                <p className="text-xs text-emerald-400">All required guidelines satisfied!</p>
                              ) : (
                                report.missing_steps?.map((step, index) => (
                                  <p key={index} className="text-xs text-red-400/90">• {step}</p>
                                ))
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Trace Reasoning */}
                        <div className="pt-2">
                          <span className="text-[10px] uppercase font-bold text-dark-500">Reasoning trace</span>
                          <p className="text-xs text-dark-300 mt-1 bg-dark-950 p-3 border border-dark-850 rounded-lg leading-relaxed whitespace-pre-wrap">{report.reasoning_trace}</p>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* TAB: METRICS ANALYTICS */}
          {activeTab === 'analytics' && (
            <div className="space-y-6">
              <h3 className="text-xs font-bold text-white uppercase mb-2">Operational Analytics</h3>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* User workload distribution */}
                <div className="bg-dark-900 border border-dark-800 p-5 rounded-xl">
                  <h4 className="text-xs font-bold text-white mb-4">Workload Distribution (Developer Load)</h4>
                  <div className="h-64">
                    {getWorkloadData().length === 0 ? (
                      <p className="text-center text-dark-500 py-16 text-xs">No active assignments to map workloads.</p>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={getWorkloadData()}>
                          <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                          <YAxis stroke="#64748b" fontSize={10} />
                          <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155' }} />
                          <Bar dataKey="tasks" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>

                {/* Meeting Workload pie chart */}
                <div className="bg-dark-900 border border-dark-800 p-5 rounded-xl">
                  <h4 className="text-xs font-bold text-white mb-4">Task Generation Distribution (per Meeting)</h4>
                  <div className="h-64 flex flex-col justify-between">
                    {getMeetingTaskData().length === 0 ? (
                      <p className="text-center text-dark-500 py-16 text-xs">No meeting metrics available.</p>
                    ) : (
                      <>
                        <div className="h-48">
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={getMeetingTaskData()}
                                cx="50%"
                                cy="50%"
                                innerRadius={40}
                                outerRadius={60}
                                dataKey="value"
                              >
                                {getMeetingTaskData().map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                              </Pie>
                              <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155' }} />
                            </PieChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="flex flex-wrap gap-3 justify-center mt-3">
                          {getMeetingTaskData().map((item, index) => (
                            <div key={index} className="flex items-center gap-1.5 text-[10px] text-dark-300">
                              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
                              <span className="truncate max-w-[120px]">{item.name} ({item.value})</span>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB: MANAGER COPILOT */}
          {activeTab === 'copilot' && (
            <div className="space-y-6">
              <div className="p-4 bg-gradient-to-r from-brand-900/20 to-dark-900 border border-brand-900/30 rounded-xl">
                <h4 className="text-xs font-bold text-white">Ask Copilot</h4>
                <p className="text-[10px] text-dark-400 mt-0.5">Request real-time data lookups regarding overdue tasks, overloaded developers, or compliance bottlenecks.</p>
              </div>

              {/* Quick pre-built queries */}
              <div>
                <span className="text-[10px] uppercase font-bold text-dark-500 block mb-2">Predefined Queries</span>
                <div className="flex flex-wrap gap-2">
                  {[
                    'What is overdue?',
                    'Who is overloaded?',
                    'What meetings created the most work?',
                    'Which SOPs are frequently violated?'
                  ].map((q, i) => (
                    <button
                      key={i}
                      onClick={() => runCopilotQuery(q)}
                      className="bg-dark-900 hover:bg-dark-800 text-dark-300 text-xs px-3.5 py-2 rounded-lg font-medium border border-dark-800 transition-all"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {/* Prompt box */}
              <div className="bg-dark-900 border border-dark-800 p-5 rounded-xl space-y-4">
                <div className="flex gap-3 items-end">
                  <div className="flex-1">
                    <label className="text-[10px] uppercase font-bold text-dark-500 block mb-2">Custom Query Prompt</label>
                    <textarea
                      placeholder="Ask the manager copilot something specific..."
                      rows={3}
                      value={copilotQuery}
                      onChange={e => setCopilotQuery(e.target.value)}
                      className="w-full bg-dark-950 border border-dark-800 rounded-lg p-3 text-xs text-white focus:outline-none focus:border-brand-500"
                    />
                  </div>
                  <button
                    onClick={() => runCopilotQuery()}
                    disabled={copilotLoading}
                    className="bg-brand-600 hover:bg-brand-500 disabled:bg-brand-800 text-white rounded-lg p-3 text-sm font-semibold flex items-center justify-center gap-1.5 transition-all h-11 shrink-0"
                  >
                    {copilotLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Bot className="h-5 w-5" />}
                    <span>Consult</span>
                  </button>
                </div>

                {/* Response area */}
                {copilotAnswer && (
                  <div className="pt-4 border-t border-dark-800">
                    <span className="text-[10px] uppercase font-bold text-dark-500 block mb-2">Copilot Analysis Response</span>
                    <div className="bg-dark-950 p-4 border border-dark-850 rounded-lg text-xs text-dark-200 whitespace-pre-wrap leading-relaxed">
                      {copilotAnswer}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      </main>

      {/* --- MODAL: NEW MEETING --- */}
      {showMeetingModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-dark-900 border border-dark-800 rounded-2xl p-6 space-y-5">
            <div className="border-b border-dark-800 pb-3 flex justify-between items-center">
              <h3 className="text-sm font-bold text-white">Ingest New Transcript</h3>
              <button onClick={() => setShowMeetingModal(false)} className="text-xs text-dark-500 hover:text-white">Cancel</button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-[10px] uppercase font-bold text-dark-400 block mb-1">Meeting Title</label>
                <input
                  type="text"
                  placeholder="e.g. Q3 Architecture Align"
                  value={newMeetingTitle}
                  onChange={e => setNewMeetingTitle(e.target.value)}
                  className="w-full bg-dark-950 border border-dark-800 rounded-lg px-3 py-2 text-xs text-white placeholder-dark-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-dark-400 block mb-1 font-medium">Transcript Dialog Content</label>
                <textarea
                  placeholder="Paste raw conversation dialog text here..."
                  rows={8}
                  value={newTranscript}
                  onChange={e => setNewTranscript(e.target.value)}
                  className="w-full bg-dark-950 border border-dark-800 rounded-lg p-3 text-xs text-white focus:outline-none"
                />
              </div>
            </div>

            <button
              onClick={createMeeting}
              className="w-full bg-brand-600 hover:bg-brand-500 text-white rounded-lg py-2.5 text-xs font-semibold transition-all"
            >
              Upload Transcript
            </button>
          </div>
        </div>
      )}

      {/* --- MODAL: NEW SOP DOCUMENT --- */}
      {showSopModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="w-full max-w-xl bg-dark-900 border border-dark-800 rounded-2xl p-6 space-y-5 max-h-[85vh] overflow-y-auto">
            <div className="border-b border-dark-800 pb-3 flex justify-between items-center">
              <h3 className="text-sm font-bold text-white">Create SOP Policy Guideline</h3>
              <button onClick={() => setShowSopModal(false)} className="text-xs text-dark-500 hover:text-white">Cancel</button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] uppercase font-bold text-dark-400 block mb-1">SOP Title</label>
                  <input
                    type="text"
                    placeholder="e.g. Migration Policy"
                    value={newSop.title}
                    onChange={e => setNewSop({ ...newSop, title: e.target.value })}
                    className="w-full bg-dark-950 border border-dark-800 rounded-lg px-3 py-2 text-xs text-white placeholder-dark-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase font-bold text-dark-400 block mb-1">Department Tag</label>
                  <select
                    value={newSop.department}
                    onChange={e => setNewSop({ ...newSop, department: e.target.value })}
                    className="w-full bg-dark-950 border border-dark-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                  >
                    <option value="Engineering">Engineering</option>
                    <option value="DevOps">DevOps</option>
                    <option value="Security">Security</option>
                    <option value="QA">QA</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-dark-400 block mb-1">SOP Policy Clauses / Sections</label>
                <div className="space-y-3">
                  {newSopSections.map((sec, idx) => (
                    <div key={idx} className="p-3 bg-dark-950 border border-dark-850 rounded-lg space-y-2 relative">
                      <div className="grid grid-cols-3 gap-2">
                        <input
                          type="text"
                          placeholder="Clause No. (1.1)"
                          value={sec.section_number}
                          onChange={e => {
                            const copy = [...newSopSections];
                            copy[idx].section_number = e.target.value;
                            setNewSopSections(copy);
                          }}
                          className="bg-dark-900 border border-dark-800 rounded px-2.5 py-1 text-xs text-white focus:outline-none"
                        />
                        <input
                          type="text"
                          placeholder="Clause Title (Purpose)"
                          value={sec.title}
                          onChange={e => {
                            const copy = [...newSopSections];
                            copy[idx].title = e.target.value;
                            setNewSopSections(copy);
                          }}
                          className="col-span-2 bg-dark-900 border border-dark-800 rounded px-2.5 py-1 text-xs text-white focus:outline-none"
                        />
                      </div>
                      <textarea
                        placeholder="Define SOP clause instruction guidelines..."
                        rows={3}
                        value={sec.content}
                        onChange={e => {
                          const copy = [...newSopSections];
                          copy[idx].content = e.target.value;
                          setNewSopSections(copy);
                        }}
                        className="w-full bg-dark-900 border border-dark-800 rounded p-2.5 text-xs text-white focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={() => setNewSopSections([...newSopSections, { section_number: '1.2', title: '', content: '' }])}
                className="w-full border border-dark-800 hover:border-dark-700 text-dark-400 hover:text-white text-xs font-semibold py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all border-dashed"
              >
                <Plus className="h-4.5 w-4.5" />
                Add Clause Section
              </button>
            </div>

            <button
              onClick={createSop}
              className="w-full bg-brand-600 hover:bg-brand-500 text-white rounded-lg py-2.5 text-xs font-semibold transition-all"
            >
              Ingest SOP Document
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
