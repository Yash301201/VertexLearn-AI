import { useEffect, useState } from 'react'
import {
	ArrowDownRight,
	ArrowRight,
	Bell,
	BookOpen,
	Check,
	CheckCircle2,
	ChevronRight,
	CircleHelp,
	Clock3,
	Compass,
	GraduationCap,
	LayoutDashboard,
	LogOut,
	Menu,
	Plus,
	Search,
	ShieldCheck,
	Sparkles,
	X,
} from 'lucide-react'
import { api, clearSession, getRememberedEmail, getSession, saveSession, setRememberedEmail } from './lib/api'
import AdminPanel from './admin-panel'
import AIStudio from './ai-studio'

const coverImages = [
	'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1000&q=85',
	'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1000&q=85',
	'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1000&q=85',
	'https://images.unsplash.com/photo-1526378722484-bd91ca387e72?auto=format&fit=crop&w=1000&q=85',
]

const navItems = [
	{ id: 'overview', label: 'Overview', icon: LayoutDashboard },
	{ id: 'explore', label: 'Explore courses', icon: Compass },
	{ id: 'learning', label: 'My learning', icon: BookOpen },
	{ id: 'assessments', label: 'Assessments', icon: CircleHelp },
	{ id: 'ai', label: 'AI Studio', icon: Sparkles },
]

function initials(name = '') {
	return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'V'
}

function titleCaseEmail(email = '') {
	const name = email.split('@')[0]?.replace(/[._-]+/g, ' ') || 'Learner'
	return name.replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function courseCategory(title = '') {
	const lower = title.toLowerCase()
	if (lower.includes('design') || lower.includes('ux')) return 'Design'
	if (lower.includes('data') || lower.includes('python')) return 'Data & AI'
	if (lower.includes('business') || lower.includes('product')) return 'Business'
	return 'Technology'
}

function App() {
	const [session, setSession] = useState(getSession)
	const [courses, setCourses] = useState([])
	const [enrollments, setEnrollments] = useState([])
	const [assessments, setAssessments] = useState([])
	const [attempts, setAttempts] = useState([])
	const [activeView, setActiveView] = useState('overview')
	const [search, setSearch] = useState('')
	const [loading, setLoading] = useState(true)
	const [loadError, setLoadError] = useState('')
	const [authOpen, setAuthOpen] = useState(() => new URLSearchParams(window.location.search).has('reset_token'))
	const [courseOpen, setCourseOpen] = useState(null)
	const [quizOpen, setQuizOpen] = useState(null)
	const [notice, setNotice] = useState('')
	const [mobileNavOpen, setMobileNavOpen] = useState(false)

	async function refreshData() {
		setLoading(true)
		setLoadError('')
		try {
			const [courseData, assessmentData] = await Promise.all([
				api('/courses/'),
				api('/assessments/'),
			])
			setCourses(courseData.courses ?? [])
			setAssessments(assessmentData.assessments ?? [])
			if (getSession().token) {
				const [enrollmentData, attemptData] = await Promise.all([
					api('/enrollments/me'),
					api('/attempts/me'),
				])
				setEnrollments(enrollmentData ?? [])
				setAttempts(attemptData ?? [])
			} else {
				setEnrollments([])
				setAttempts([])
			}
		} catch (error) {
			setLoadError(error.message || 'We could not reach the learning service.')
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		refreshData()
	}, [session.token])

	useEffect(() => {
		function handleSessionExpired() {
			setSession({ token: null, user: null })
			setEnrollments([])
			setAttempts([])
			setAuthOpen(true)
			setNotice('Your session expired. Please sign in again.')
		}
		window.addEventListener('vertexlearn:session-expired', handleSessionExpired)
		return () => window.removeEventListener('vertexlearn:session-expired', handleSessionExpired)
	}, [])

	useEffect(() => {
		if (!notice) return undefined
		const timeout = window.setTimeout(() => setNotice(''), 3200)
		return () => window.clearTimeout(timeout)
	}, [notice])

	const enrolledIds = new Set(enrollments.map((item) => item.course_id))
	const readyAssessments = assessments.filter((assessment) => assessment.ready)
	const enrolledCourses = enrollments.map((enrollment) => ({
		...enrollment,
		...courses.find((course) => course.id === enrollment.course_id),
	})).filter((course) => course.id)
	const query = search.trim().toLowerCase()
	const visibleCourses = courses.filter((course) =>
		`${course.title} ${course.description} ${course.instructor}`.toLowerCase().includes(query),
	)
	const completedCourses = enrolledCourses.filter((course) => course.progress_percent >= 100).length
	const overallProgress = enrolledCourses.length
		? Math.round(enrolledCourses.reduce((sum, course) => sum + course.progress_percent, 0) / enrolledCourses.length)
		: 0
	const learnerName = session.user?.name || titleCaseEmail(session.user?.email)
	const visibleNavItems = session.user?.role === 'admin'
		? [...navItems, { id: 'admin', label: 'Admin', icon: ShieldCheck }]
		: navItems

	async function handleAuth(credentials, mode) {
		if (mode === 'forgot') {
			await api('/auth/forgot-password', {
				method: 'POST',
				body: JSON.stringify({ email: credentials.email }),
			})
			return
		}
		if (mode === 'reset') {
			await api('/auth/reset-password', {
				method: 'POST',
				body: JSON.stringify({ token: credentials.token, password: credentials.password }),
			})
			setNotice('Password updated. Sign in with your new password.')
			return
		}
		if (mode === 'register') {
			await api('/auth/register', { method: 'POST', body: JSON.stringify(credentials) })
		}
		const result = await api('/auth/login', {
			method: 'POST',
			body: JSON.stringify({ email: credentials.email, password: credentials.password }),
		})
		let user = {
			name: credentials.name || titleCaseEmail(result.email),
			email: result.email,
			role: result.role,
		}
		saveSession(result.access_token, user)
		try {
			user = await api('/auth/me')
		} catch {
			// Keep the login response as a fallback if profile loading is unavailable.
		}
		saveSession(result.access_token, user)
		setSession({ token: result.access_token, user })
		setAuthOpen(false)
		setNotice(`Welcome in, ${user.name.split(' ')[0]}.`)
	}

	function handleLogout() {
		clearSession()
		setSession({ token: null, user: null })
		setActiveView('overview')
		setNotice('You have signed out.')
	}

	async function enroll(course) {
		if (!session.token) {
			setAuthOpen(true)
			return
		}
		try {
			await api(`/enrollments/courses/${course.id}`, { method: 'POST' })
			await refreshData()
			const lessonData = await api(`/courses/${course.id}/lessons`)
			setCourseOpen((current) => current?.course.id === course.id
				? { ...current, lessons: lessonData.lessons ?? [], loading: false, error: '', progressPercent: 0 }
				: current)
			setNotice(`You are enrolled in ${course.title}.`)
		} catch (error) {
			setNotice(error.message)
		}
	}

	async function openCourse(course) {
		const courseId = course.course_id ?? course.id
		const isEnrolled = enrolledIds.has(courseId)
		const enrollment = enrollments.find((item) => item.course_id === courseId)
		setCourseOpen({ course, lessons: [], loading: isEnrolled, error: '', progressPercent: enrollment?.progress_percent ?? 0 })
		if (!isEnrolled) return
		try {
			const data = await api(`/courses/${course.id}/lessons`)
			setCourseOpen((current) => current?.course.id === course.id
				? { ...current, lessons: data.lessons ?? [], loading: false }
				: current)
		} catch (error) {
			setCourseOpen((current) => current?.course.id === course.id
				? { ...current, loading: false, error: error.message }
				: current)
		}
	}

	async function completeLesson(lesson) {
		try {
			const result = await api(
				`/enrollments/courses/${courseOpen.course.id}/lessons/${lesson.id}/complete`,
				{ method: 'POST' },
			)
			setEnrollments((current) => current.map((enrollment) =>
				enrollment.course_id === result.course_id
					? { ...enrollment, progress_percent: result.progress_percent }
					: enrollment,
			))
			setCourseOpen((current) => current?.course.id === result.course_id
				? {
					...current,
					progressPercent: result.progress_percent,
					lessons: current.lessons.map((item) =>
						item.id === result.lesson_id ? { ...item, completed: true } : item,
					),
				}
				: current)
			setNotice('Lesson marked complete.')
		} catch (error) {
			setNotice(error.message)
		}
	}

	async function startAssessment(assessment) {
		if (!session.token) {
			setAuthOpen(true)
			return
		}
		try {
			const [details, questionData] = await Promise.all([
				api(`/assessments/${assessment.id}`),
				api(`/assessments/${assessment.id}/questions`),
			])
			if (!questionData.questions?.length) {
				setNotice('This assessment is not ready yet.')
				return
			}
			setQuizOpen({ assessment: details.assessment, questions: questionData.questions, answers: {}, result: null })
		} catch (error) {
			setNotice(error.message)
		}
	}

	async function submitAssessment() {
		const answers = Object.entries(quizOpen.answers).map(([questionId, selected]) => ({
			question_id: Number(questionId),
			selected_option_index: selected,
		}))
		try {
			const result = await api(`/attempts/assessments/${quizOpen.assessment.id}`, {
				method: 'POST',
				body: JSON.stringify({ answers }),
			})
			setQuizOpen((current) => ({ ...current, result }))
			setAttempts((current) => [result, ...current])
		} catch (error) {
			setNotice(error.message)
		}
	}

	function navigate(view) {
		setActiveView(view)
		setMobileNavOpen(false)
		setSearch('')
	}

	const pageTitle = {
		overview: 'Your learning space',
		explore: 'Explore courses',
		learning: 'My learning',
		assessments: 'Assessments',
		ai: 'AI Studio',
		admin: 'Admin workspace',
	}[activeView]

	return (
		<div className="app-shell">
			<aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
				<a className="brand" href="#overview" onClick={() => navigate('overview')}>
					<span className="brand-mark"><GraduationCap size={22} strokeWidth={2.2} /></span>
					<span>vertex<span className="brand-light">learn</span><small>AI learning space</small></span>
				</a>

				<div className="sidebar-label">Workspace</div>
				<nav className="side-nav" aria-label="Main navigation">
					{visibleNavItems.map(({ id, label, icon: Icon }) => (
						<button
							className={`nav-link ${activeView === id ? 'nav-link-active' : ''}`}
							key={id}
							onClick={() => navigate(id)}
						>
							<Icon size={18} strokeWidth={1.9} />
							<span>{label}</span>
							{id === 'learning' && enrolledCourses.length > 0 && <span className="nav-count">{enrolledCourses.length}</span>}
						</button>
					))}
				</nav>

				<div className="sidebar-bottom">
					<div className="sidebar-note">
						<span className="note-icon"><Sparkles size={16} /></span>
						<p>Small steps add up.<br /><strong>Keep your pace.</strong></p>
						<ArrowDownRight size={17} className="note-arrow" />
					</div>
					{session.token ? (
						<button className="profile-row" onClick={handleLogout} title="Sign out">
							<span className="avatar">{initials(learnerName)}</span>
							<span className="profile-copy"><strong>{learnerName}</strong><small>{session.user?.role === 'admin' ? 'Administrator' : 'Learner'}</small></span>
							<LogOut size={16} className="logout-icon" />
						</button>
					) : (
						<button className="profile-row guest-profile" onClick={() => setAuthOpen(true)}>
							<span className="avatar avatar-guest">V</span>
							<span className="profile-copy"><strong>Your profile</strong><small>Sign in to get started</small></span>
							<ChevronRight size={16} />
						</button>
					)}
				</div>
			</aside>

			<main className="main-area">
				<header className="topbar">
					<button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileNavOpen(!mobileNavOpen)}>
						{mobileNavOpen ? <X size={19} /> : <Menu size={19} />}
					</button>
					<div className="breadcrumb"><span>Workspace</span><ChevronRight size={14} /><strong>{pageTitle}</strong></div>
					<div className="topbar-actions">
						<label className="search-box">
							<Search size={17} />
							<input aria-label="Search courses" placeholder="Search courses" value={search} onChange={(event) => setSearch(event.target.value)} />
							<kbd>/</kbd>
						</label>
						<button className="icon-button notification-button" aria-label="Notifications" onClick={() => setNotice('You are all caught up.') }><Bell size={18} /><i /></button>
						{!session.token && <button className="top-signin" onClick={() => setAuthOpen(true)}>Sign in <ArrowRight size={15} /></button>}
					</div>
				</header>

				<div className="page-content">
					{loadError && (
						<div className="error-banner"><span>{loadError}</span><button onClick={refreshData}>Try again</button></div>
					)}
					{activeView === 'overview' && (
						<>
							<section className="welcome-row">
								<div>
									<div className="eyebrow"><span className="eyebrow-dot" /> YOUR PERSONAL LEARNING SPACE</div>
									<h1>{session.token ? <>Good to see you, <span>{learnerName.split(' ')[0]}.</span></> : <>Make room for<br /><span>what’s next.</span></>}</h1>
									<p className="welcome-copy">A little learning today can take you somewhere new tomorrow.</p>
								</div>
								<div className="date-stamp"><span className="date-day">{new Intl.DateTimeFormat('en', { day: '2-digit' }).format(new Date())}</span><span>{new Intl.DateTimeFormat('en', { month: 'short', year: 'numeric' }).format(new Date())}</span></div>
							</section>

							<section className="stats-row" aria-label="Learning summary">
								<article className="stat-block"><span className="stat-label">IN PROGRESS</span><strong>{session.token ? enrolledCourses.length.toString().padStart(2, '0') : '—'}</strong><span className="stat-detail">{session.token ? 'courses in your library' : 'sign in to track progress'}</span><span className="stat-symbol stat-symbol-green"><BookOpen size={19} /></span></article>
								<article className="stat-block"><span className="stat-label">OVERALL PROGRESS</span><strong>{session.token ? `${overallProgress}%` : '—'}</strong><span className="stat-detail">{session.token ? `${completedCourses} courses completed` : 'your progress lives here'}</span><span className="stat-symbol stat-symbol-orange"><ArrowDownRight size={19} /></span></article>
								<article className="stat-block"><span className="stat-label">ASSESSMENTS</span><strong>{session.token ? attempts.length.toString().padStart(2, '0') : '—'}</strong><span className="stat-detail">{session.token ? 'attempts completed' : 'practice as you learn'}</span><span className="stat-symbol stat-symbol-blue"><CheckCircle2 size={19} /></span></article>
							</section>

							{session.token && enrolledCourses.length > 0 && (
								<section className="continue-section">
									<div className="section-heading"><div><span className="section-kicker">PICK UP WHERE YOU LEFT OFF</span><h2>Keep your momentum</h2></div><button className="text-action" onClick={() => navigate('learning')}>All my learning <ArrowRight size={16} /></button></div>
									<div className="continue-card">
										<div className="continue-image" style={{ backgroundImage: `url(${coverImages[enrolledCourses[0].course_id % coverImages.length]})` }}><span className="image-label"><Sparkles size={13} /> YOUR CLASSROOM</span></div>
										<div className="continue-info"><div className="course-meta"><span>{courseCategory(enrolledCourses[0].title)}</span><span className="meta-divider">·</span><span>{enrolledCourses[0].instructor || 'VertexLearn'}</span></div><h3>{enrolledCourses[0].title}</h3><p>{enrolledCourses[0].description || 'Your next lesson is waiting when you are.'}</p><div className="progress-line"><span><i style={{ width: `${enrolledCourses[0].progress_percent}%` }} /></span><small>{enrolledCourses[0].progress_percent}% complete</small></div><button className="primary-button" onClick={() => openCourse(enrolledCourses[0])}>Continue learning <ArrowRight size={16} /></button></div>
										<div className="continue-index"><span>01</span><span>/ {String(enrolledCourses.length).padStart(2, '0')}</span></div>
									</div>
								</section>
							)}

							<section className="courses-section">
								<div className="section-heading"><div><span className="section-kicker">A GOOD PLACE TO BEGIN</span><h2>{search ? 'Search results' : session.token ? 'Find your next subject' : 'Explore the course library'}</h2></div><button className="text-action" onClick={() => navigate('explore')}>Browse all <ArrowRight size={16} /></button></div>
								<CourseGrid courses={visibleCourses.slice(0, 3)} loading={loading} enrolledIds={enrolledIds} onEnroll={enroll} onOpen={openCourse} />
							</section>

							<footer className="page-footer"><span>Learn with intention.</span><span>VERTEXLEARN AI <i>·</i> {new Date().getFullYear()}</span></footer>
						</>
					)}

					{activeView === 'explore' && (
						<section className="view-section"><div className="view-intro"><div className="eyebrow"><span className="eyebrow-dot" /> THE COURSE LIBRARY</div><h1>Follow your <span>curiosity.</span></h1><p>Explore the subjects and skills you’ve been meaning to get into.</p></div><div className="section-heading"><div><span className="section-kicker">{visibleCourses.length} {visibleCourses.length === 1 ? 'COURSE' : 'COURSES'}</span><h2>{search ? `Results for “${search}”` : 'All courses'}</h2></div><span className="sort-note"><Compass size={15} /> Made for your next step</span></div><CourseGrid courses={visibleCourses} loading={loading} enrolledIds={enrolledIds} onEnroll={enroll} onOpen={openCourse} /></section>
					)}

					{activeView === 'learning' && (
						<section className="view-section"><div className="view-intro"><div className="eyebrow"><span className="eyebrow-dot" /> YOUR PERSONAL LIBRARY</div><h1>Learning, <span>your way.</span></h1><p>Everything you’re working on, all in one place.</p></div>{!session.token ? <SignInPrompt onSignIn={() => setAuthOpen(true)} /> : <><div className="section-heading"><div><span className="section-kicker">YOUR COURSES</span><h2>{enrolledCourses.length ? 'Currently in your library' : 'A fresh start'}</h2></div><button className="text-action" onClick={() => navigate('explore')}>Explore courses <ArrowRight size={16} /></button></div><CourseGrid courses={enrolledCourses} loading={loading} enrolledIds={enrolledIds} onEnroll={enroll} onOpen={openCourse} /></>}</section>
					)}

					{activeView === 'assessments' && (
						<section className="view-section"><div className="view-intro"><div className="eyebrow"><span className="eyebrow-dot" /> PRACTICE & REFLECT</div><h1>Check in with <span>yourself.</span></h1><p>Assessments are a useful pause to notice how far you’ve come.</p></div>{!session.token && <SignInPrompt onSignIn={() => setAuthOpen(true)} />}<div className="section-heading"><div><span className="section-kicker">AVAILABLE TO YOU</span><h2>Assessments</h2></div></div>{loading ? <LoadingState /> : readyAssessments.length === 0 ? <EmptyState title="No assessments just yet" detail="When assessments are added to your courses, they’ll appear here." /> : <div className="assessment-list">{readyAssessments.map((assessment, index) => { const course = courses.find((item) => item.id === assessment.course_id); const isEnrolled = enrolledIds.has(assessment.course_id); const attempt = attempts.find((item) => item.assessment_id === assessment.id); return <article className="assessment-row" key={assessment.id}><span className="assessment-number">{String(index + 1).padStart(2, '0')}</span><span className="assessment-icon"><CircleHelp size={19} /></span><div className="assessment-copy"><h3>{assessment.title}</h3><p>{course?.title || 'Course assessment'} <i>·</i> {assessment.question_count} questions <i>·</i> Pass mark {assessment.passing_score}%</p></div>{attempt && <span className={`attempt-badge ${attempt.passed ? 'attempt-passed' : ''}`}>{attempt.score}% {attempt.passed ? 'passed' : 'complete'}</span>}<button className="round-arrow" aria-label={`Start ${assessment.title}`} onClick={() => isEnrolled || session.user?.role === 'admin' ? startAssessment(assessment) : course ? enroll(course) : setAuthOpen(true)}>{isEnrolled || session.user?.role === 'admin' ? <ArrowRight size={17} /> : <Plus size={17} />}</button></article>})}</div>}</section>
					)}

					{activeView === 'admin' && session.user?.role === 'admin' && (
						<AdminPanel onNotice={setNotice} />
					)}

					{activeView === 'ai' && (
						<AIStudio
							courses={courses}
							enrollments={enrollments}
							session={session}
							onSignIn={() => setAuthOpen(true)}
							onExplore={() => navigate('explore')}
						/>
					)}
				</div>
			</main>

			{mobileNavOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}
			{authOpen && <AuthDialog onClose={() => setAuthOpen(false)} onSubmit={handleAuth} />}
			{courseOpen && <CourseDialog courseState={courseOpen} enrolled={enrolledIds.has(courseOpen.course.id)} hasSession={Boolean(session.token)} onClose={() => setCourseOpen(null)} onEnroll={() => enroll(courseOpen.course)} onComplete={completeLesson} />}
			{quizOpen && <QuizDialog quiz={quizOpen} onClose={() => setQuizOpen(null)} onAnswer={(questionId, value) => setQuizOpen((current) => ({ ...current, answers: { ...current.answers, [questionId]: value } }))} onSubmit={submitAssessment} />}
			{notice && <div className="toast" role="status"><Check size={16} />{notice}<button aria-label="Dismiss" onClick={() => setNotice('')}><X size={15} /></button></div>}
		</div>
	)
}

function CourseGrid({ courses, loading, enrolledIds, onOpen }) {
	if (loading) return <LoadingState />
	if (!courses.length) return <EmptyState title="Nothing here yet" detail="Courses will show up here as soon as your learning library is ready." />
	return <div className="course-grid">{courses.map((course, index) => { const enrolled = enrolledIds.has(course.course_id ?? course.id); const courseId = course.course_id ?? course.id; return <article className="course-card" key={`${courseId}-${index}`}><button className="course-cover" onClick={() => onOpen(course)} style={{ backgroundImage: `url(${coverImages[courseId % coverImages.length]})` }} aria-label={`Open ${course.title}`}><span className={`category-tag category-${index % 3}`}>{courseCategory(course.title)}</span><span className="cover-arrow"><ArrowUpRightIcon /></span></button><div className="course-card-body"><div className="course-meta"><span>{course.instructor || 'VertexLearn'}</span><span className="meta-divider">·</span><span><Clock3 size={13} /> Self-paced</span></div><h3>{course.title}</h3><p>{course.description || 'A practical course to help you build knowledge and move forward.'}</p>{enrolled ? <><div className="card-progress"><span><i style={{ width: `${course.progress_percent || 0}%` }} /></span><small>{course.progress_percent || 0}%</small></div><button className="course-button course-button-enrolled" onClick={() => onOpen(course)}>Continue learning <ArrowRight size={15} /></button></> : <button className="course-button" onClick={() => onOpen(course)}>View course <ArrowRight size={15} /></button>}</div></article>})}</div>
}

function ArrowUpRightIcon() {
	return <ArrowRight size={17} />
}

function LoadingState() {
	return <div className="loading-grid" aria-label="Loading courses"><span /><span /><span /></div>
}

function EmptyState({ title, detail }) {
	return <div className="empty-state"><span className="empty-icon"><BookOpen size={20} /></span><strong>{title}</strong><p>{detail}</p></div>
}

function SignInPrompt({ onSignIn }) {
	return <div className="signin-prompt"><span className="prompt-sparkle"><Sparkles size={18} /></span><div><strong>Your learning journey starts here.</strong><p>Sign in to see your courses, save your progress, and take assessments.</p></div><button className="primary-button" onClick={onSignIn}>Sign in <ArrowRight size={16} /></button></div>
}

function AuthDialog({ onClose, onSubmit }) {
	const [mode, setMode] = useState(() => new URLSearchParams(window.location.search).has('reset_token') ? 'reset' : 'login')
	const [name, setName] = useState('')
	const [email, setEmail] = useState(getRememberedEmail)
	const [rememberEmail, setRememberEmail] = useState(() => Boolean(getRememberedEmail()))
	const [password, setPassword] = useState('')
	const [error, setError] = useState('')
	const [confirmation, setConfirmation] = useState('')
	const [pending, setPending] = useState(false)

	async function submit(event) {
		event.preventDefault()
		setPending(true)
		setError('')
		setConfirmation('')
		if (mode === 'login' || mode === 'register') setRememberedEmail(email.trim(), rememberEmail)
		try {
			const token = new URLSearchParams(window.location.search).get('reset_token')
			await onSubmit({ name, email, password, token }, mode)
			if (mode === 'forgot') {
				setConfirmation('If an account exists and email delivery is configured, reset instructions will be sent.')
			}
			if (mode === 'reset') {
				const resetUrl = new URL(window.location.href)
				resetUrl.searchParams.delete('reset_token')
				window.history.replaceState({}, '', resetUrl)
				setPassword('')
				setMode('login')
			}
		} catch (submitError) {
			setError(submitError.message)
		} finally {
			setPending(false)
		}
	}

	const titles = {
		login: ['Welcome back.', 'Pick up right where you left off.'],
		register: ['Start something good.', 'Create your account and make learning yours.'],
		forgot: ['Reset your password.', 'Request a secure password reset link for your account.'],
		reset: ['Choose a new password.', 'Your reset link expires after 30 minutes.'],
	}
	return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
		<section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
			<button className="modal-close" aria-label="Close" onClick={onClose}><X size={19} /></button>
			<span className="auth-mark"><GraduationCap size={23} /></span>
			<div className="eyebrow"><span className="eyebrow-dot" /> YOUR NEXT CHAPTER</div>
			<h2 id="auth-title">{titles[mode][0]}</h2>
			<p className="dialog-subtitle">{titles[mode][1]}</p>
			<form className="auth-form" onSubmit={submit}>
				{mode === 'register' && <label>Your name<input autoComplete="name" required value={name} onChange={(event) => setName(event.target.value)} placeholder="How should we call you?" /></label>}
				{mode !== 'reset' && <label>Email address<input autoComplete="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label>}
				{mode !== 'forgot' && <label>{mode === 'reset' ? 'New password' : 'Password'}<input autoComplete={mode === 'login' ? 'current-password' : 'new-password'} type="password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" /></label>}
				{mode === 'login' && <label className="remember-email"><input type="checkbox" checked={rememberEmail} onChange={(event) => setRememberEmail(event.target.checked)} /><span>Remember my email on this device</span></label>}
				{confirmation && <p className="form-confirmation" role="status">{confirmation}</p>}
				{error && <p className="form-error" role="alert">{error}</p>}
				<button className="primary-button auth-submit" disabled={pending}>{pending ? 'One moment…' : mode === 'login' ? 'Sign in' : mode === 'register' ? 'Create account' : mode === 'forgot' ? 'Send reset link' : 'Update password'} <ArrowRight size={16} /></button>
			</form>
			<p className="auth-switch">{mode === 'login' ? <>New to VertexLearn? <button onClick={() => { setMode('register'); setError(''); setConfirmation('') }}>Create an account</button></> : mode === 'register' ? <>Already have an account? <button onClick={() => { setMode('login'); setError(''); setConfirmation('') }}>Sign in instead</button></> : <>Remembered your password? <button onClick={() => { setMode('login'); setError(''); setConfirmation('') }}>Back to sign in</button></>}</p>
			{mode === 'login' && <p className="auth-switch auth-forgot"><button onClick={() => { setMode('forgot'); setError(''); setConfirmation('') }}>Forgot your password?</button></p>}
			<span className="auth-footnote">LEARN AT YOUR OWN PACE</span>
		</section>
	</div>
}

function CourseDialog({ courseState, enrolled, hasSession, onClose, onEnroll, onComplete }) {
	const { course, lessons, loading, error, progressPercent = 0 } = courseState
	const [expandedLessonId, setExpandedLessonId] = useState(null)
	return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
		<section className="course-dialog" role="dialog" aria-modal="true" aria-labelledby="course-title">
			<button className="modal-close" aria-label="Close" onClick={onClose}><X size={19} /></button>
			<div className="dialog-cover" style={{ backgroundImage: `url(${coverImages[course.id % coverImages.length]})` }}>
				<span className="image-label"><Sparkles size={13} /> COURSE OVERVIEW</span>
			</div>
			<div className="course-dialog-content">
				<div className="course-meta"><span>{courseCategory(course.title)}</span><span className="meta-divider">·</span><span>{course.instructor || 'VertexLearn'}</span></div>
				<h2 id="course-title">{course.title}</h2>
				<p className="course-dialog-description">{course.description || 'Explore the course content and take your next step.'}</p>
				{!enrolled && <div className="enroll-callout"><span><BookOpen size={18} /></span><div><strong>Ready when you are.</strong><p>Enroll to unlock the lessons and track your progress.</p></div><button className="primary-button" onClick={onEnroll}>{hasSession ? 'Enroll now' : 'Sign in to enroll'} <ArrowRight size={15} /></button></div>}
				{enrolled && <div className="course-progress">
					<div className="course-progress-label"><span>YOUR PROGRESS</span><strong>{progressPercent}% complete</strong></div>
					<div className="course-progress-track"><i style={{ width: `${progressPercent}%` }} /></div>
				</div>}
				<div className="lesson-heading"><div><span className="section-kicker">COURSE CONTENT</span><h3>{lessons.length} lessons</h3></div>{enrolled && <span className="lesson-access">YOUR CLASSROOM</span>}</div>
				{loading ? <LoadingState /> : error ? <div className="inline-error">{error}</div> : lessons.length ? <div className="lesson-list">{lessons.map((lesson, index) => <article className={`lesson-row ${lesson.completed ? 'lesson-row-completed' : ''}`} key={lesson.id}>
					<span className="lesson-index">{String(index + 1).padStart(2, '0')}</span><span className="lesson-play"><BookOpen size={16} /></span>
					<div className="lesson-copy"><strong>{lesson.title}</strong><span>{lesson.content?.slice(0, 110) || 'Lesson content'}{lesson.content?.length > 110 ? '…' : ''}</span>{expandedLessonId === lesson.id && <p className="lesson-full-content">{lesson.content}</p>}</div>
					{enrolled && <div className="lesson-actions"><button className="lesson-read" onClick={() => setExpandedLessonId((current) => current === lesson.id ? null : lesson.id)}>{expandedLessonId === lesson.id ? 'Close lesson' : 'Read lesson'}</button>{lesson.completed ? <span className="lesson-completed"><Check size={16} /> Completed</span> : <button className="lesson-done" title="Mark lesson complete" onClick={() => onComplete(lesson)}>Mark complete</button>}</div>}
				</article>)}</div> : <EmptyState title="Lessons are on their way" detail="The instructor hasn’t added course content yet." />}
			</div>
		</section>
	</div>
}

function QuizDialog({ quiz, onClose, onAnswer, onSubmit }) {
	const answeredCount = Object.keys(quiz.answers).length
	return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="quiz-dialog" role="dialog" aria-modal="true" aria-labelledby="quiz-title"><button className="modal-close" aria-label="Close" onClick={onClose}><X size={19} /></button>{quiz.result ? <div className="quiz-result"><span className={`result-mark ${quiz.result.passed ? 'result-pass' : ''}`}><CheckCircle2 size={29} /></span><span className="section-kicker">ASSESSMENT COMPLETE</span><h2>{quiz.result.passed ? 'Nicely done.' : 'Good practice.'}</h2><p>You scored <strong>{quiz.result.score}%</strong>. {quiz.result.passed ? 'You passed this assessment.' : 'Take what you learned into your next attempt.'}</p><button className="primary-button" onClick={onClose}>Back to assessments <ArrowRight size={16} /></button></div> : <><span className="eyebrow"><span className="eyebrow-dot" /> {quiz.questions.length} QUESTIONS</span><h2 id="quiz-title">{quiz.assessment.title}</h2><p className="dialog-subtitle">Choose the best answer for each question.</p><div className="quiz-questions">{quiz.questions.map((question, index) => <fieldset className="quiz-question" key={question.id}><legend><span>{String(index + 1).padStart(2, '0')}</span>{question.prompt}</legend>{question.options.map((option, optionIndex) => <label className={`quiz-option ${quiz.answers[question.id] === optionIndex ? 'quiz-option-selected' : ''}`} key={`${question.id}-${optionIndex}`}><input type="radio" name={`question-${question.id}`} checked={quiz.answers[question.id] === optionIndex} onChange={() => onAnswer(question.id, optionIndex)} /><span className="radio-mark" />{option}</label>)}</fieldset>)}</div><div className="quiz-footer"><span>{answeredCount} of {quiz.questions.length} answered</span><button className="primary-button" disabled={answeredCount !== quiz.questions.length} onClick={onSubmit}>Submit answers <ArrowRight size={16} /></button></div></>}</section></div>
}

export default App
