// Where each role lands after login.
export const homePathForRole = (role) => (role === 'coordinator' ? '/coordinator' : '/student')
