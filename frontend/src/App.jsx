import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import { AuthProvider } from './context/AuthContext'
import CoordinatorAnalytics from './pages/coordinator/Analytics'
import CoordinatorApplications from './pages/coordinator/Applications'
import CoordinatorCompanies from './pages/coordinator/Companies'
import CoordinatorDashboard from './pages/coordinator/Dashboard'
import CoordinatorJobs from './pages/coordinator/Jobs'
import CoordinatorProgress from './pages/coordinator/Progress'
import CoordinatorReports from './pages/coordinator/Reports'
import CoordinatorStudentDetail from './pages/coordinator/StudentDetail'
import CoordinatorStudents from './pages/coordinator/Students'
import Home from './pages/Home'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import Register from './pages/Register'
import ApplicationDetails from './pages/student/ApplicationDetails'
import Applications from './pages/student/Applications'
import Chatbot from './pages/student/Chatbot'
import Dashboard from './pages/student/Dashboard'
import Companies from './pages/student/Companies'
import InterviewDetails from './pages/student/InterviewDetails'
import Interviews from './pages/student/Interviews'
import JobDetails from './pages/student/JobDetails'
import Jobs from './pages/student/Jobs'
import Profile from './pages/student/Profile'
import Recommendations from './pages/student/Recommendations'
import Resume from './pages/student/Resume'
import ResumeAnalysis from './pages/student/ResumeAnalysis'
import SkillGap from './pages/student/SkillGap'
import ProtectedRoute from './routes/ProtectedRoute'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="min-h-screen bg-slate-50">
          <Navbar />
          <main>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              <Route element={<ProtectedRoute role="student" />}>
                <Route path="/student" element={<Dashboard />} />
                <Route path="/student/profile" element={<Profile />} />
                <Route path="/student/jobs" element={<Jobs />} />
                <Route path="/student/jobs/:id" element={<JobDetails />} />
                <Route path="/student/companies" element={<Companies />} />
                <Route path="/student/recommendations" element={<Recommendations />} />
                <Route path="/student/resume" element={<Resume />} />
                <Route path="/student/resume/analysis" element={<ResumeAnalysis />} />
                <Route path="/student/skill-gap" element={<SkillGap />} />
                <Route path="/student/chat" element={<Chatbot />} />
                <Route path="/student/applications" element={<Applications />} />
                <Route path="/student/applications/:id" element={<ApplicationDetails />} />
                <Route path="/student/interviews" element={<Interviews />} />
                <Route path="/student/interviews/:id" element={<InterviewDetails />} />
              </Route>
              <Route element={<ProtectedRoute role="coordinator" />}>
                <Route path="/coordinator" element={<CoordinatorDashboard />} />
                <Route path="/coordinator/students" element={<CoordinatorStudents />} />
                <Route path="/coordinator/students/:id" element={<CoordinatorStudentDetail />} />
                <Route path="/coordinator/companies" element={<CoordinatorCompanies />} />
                <Route path="/coordinator/jobs" element={<CoordinatorJobs />} />
                <Route path="/coordinator/applications" element={<CoordinatorApplications />} />
                <Route path="/coordinator/progress" element={<CoordinatorProgress />} />
                <Route path="/coordinator/analytics" element={<CoordinatorAnalytics />} />
                <Route path="/coordinator/reports" element={<CoordinatorReports />} />
              </Route>

              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </AuthProvider>
    </BrowserRouter>
  )
}
