import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import { AuthProvider } from './context/AuthContext'
import CoordinatorHome from './pages/CoordinatorHome'
import Home from './pages/Home'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import Register from './pages/Register'
import StudentHome from './pages/StudentHome'
import Companies from './pages/student/Companies'
import JobDetails from './pages/student/JobDetails'
import Jobs from './pages/student/Jobs'
import Profile from './pages/student/Profile'
import Recommendations from './pages/student/Recommendations'
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
