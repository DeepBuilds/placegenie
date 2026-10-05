import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import { AuthProvider } from './context/AuthContext'
import CoordinatorHome from './pages/CoordinatorHome'
import Home from './pages/Home'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import Register from './pages/Register'
import StudentHome from './pages/StudentHome'
import Profile from './pages/student/Profile'
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
