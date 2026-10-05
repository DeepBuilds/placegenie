import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import { AuthProvider } from './context/AuthContext'
import CoordinatorHome from './pages/CoordinatorHome'
import Home from './pages/Home'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import Register from './pages/Register'
import StudentHome from './pages/StudentHome'
import ApplicationDetails from './pages/student/ApplicationDetails'
import Applications from './pages/student/Applications'
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
                <Route path="/student" element={<StudentHome />} />
                <Route path="/student/profile" element={<Profile />} />
                <Route path="/student/jobs" element={<Jobs />} />
                <Route path="/student/jobs/:id" element={<JobDetails />} />
                <Route path="/student/companies" element={<Companies />} />
                <Route path="/student/recommendations" element={<Recommendations />} />
                <Route path="/student/resume" element={<Resume />} />
                <Route path="/student/resume/analysis" element={<ResumeAnalysis />} />
                <Route path="/student/skill-gap" element={<SkillGap />} />
                <Route path="/student/applications" element={<Applications />} />
                <Route path="/student/applications/:id" element={<ApplicationDetails />} />
                <Route path="/student/interviews" element={<Interviews />} />
                <Route path="/student/interviews/:id" element={<InterviewDetails />} />
              </Route>
              <Route element={<ProtectedRoute role="coordinator" />}>
                <Route path="/coordinator" element={<CoordinatorHome />} />
              </Route>

              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </AuthProvider>
    </BrowserRouter>
  )
}
