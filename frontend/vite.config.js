import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
	plugins: [react()],
	server: {
		proxy: Object.fromEntries(
			['/auth', '/courses', '/enrollments', '/assessments', '/attempts', '/users', '/ai'].map((path) => [
				path,
				'http://127.0.0.1:8000',
			]),
		),
	},
})
