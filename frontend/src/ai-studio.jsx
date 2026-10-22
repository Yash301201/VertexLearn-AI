import { useState } from 'react'
import { ArrowRight, BookOpen, Check, LoaderCircle, Send, Sparkles, X } from 'lucide-react'
import { api } from './lib/api'

export default function AIStudio({ courses, enrollments, session, onSignIn, onExplore }) {
	const [selectedCourseId, setSelectedCourseId] = useState('')
	const [question, setQuestion] = useState('')
	const [messages, setMessages] = useState([])
	const [error, setError] = useState('')
	const [pending, setPending] = useState(false)
	const [reviewingPlanId, setReviewingPlanId] = useState(null)

	const availableCourses = session.user?.role === 'admin'
		? courses
		: enrollments.map((enrollment) => courses.find((course) => course.id === enrollment.course_id)).filter(Boolean)
	const preferredCourse = availableCourses.find((course) => course.title.startsWith('Applied AI:')) || availableCourses[0]
	const activeCourseId = selectedCourseId || String(preferredCourse?.id || '')

	async function submitQuestion(event) {
		event.preventDefault()
		if (!question.trim() || !activeCourseId) return

		const submittedQuestion = question.trim()
		setQuestion('')
		setError('')
		setPending(true)
		try {
			const response = await api('/ai/agent', {
				method: 'POST',
				body: JSON.stringify({ course_id: Number(activeCourseId), question: submittedQuestion }),
			})
			setMessages((current) => [...current, {
				question: submittedQuestion,
				answer: response.answer,
				sources: response.sources ?? [],
				intent: response.intent,
				progress: response.progress,
				plan: response.plan,
			}])
		} catch (requestError) {
			setQuestion(submittedQuestion)
			setError(requestError.message)
		} finally {
			setPending(false)
		}
	}

	async function reviewPlan(planId, decision, messageIndex) {
		setError('')
		setReviewingPlanId(planId)
		try {
			const response = await api(`/ai/plans/${planId}/${decision}`, { method: 'POST' })
			setMessages((current) => current.map((message, index) => (
				index === messageIndex ? { ...message, plan: response.plan } : message
			)))
		} catch (requestError) {
			setError(requestError.message)
		} finally {
			setReviewingPlanId(null)
		}
	}

	return <section className="view-section ai-studio-view">
		<div className="view-intro">
			<div className="eyebrow"><span className="eyebrow-dot" /> COURSE-GROUNDED PROJECT</div>
			<h1>AI study <span>assistant.</span></h1>
			<p>Ask a course question or request a study plan based on your learning progress.</p>
		</div>
		{!session.token ? <div className="ai-empty-state">
			<span className="ai-empty-icon"><Sparkles size={20} /></span>
			<strong>Sign in to use your study assistant.</strong>
			<button className="primary-button" onClick={onSignIn}>Sign in <ArrowRight size={15} /></button>
		</div> : availableCourses.length === 0 ? <div className="ai-empty-state">
			<span className="ai-empty-icon"><BookOpen size={20} /></span>
			<strong>Enroll in a course to ask lesson-based questions.</strong>
			<button className="primary-button" onClick={onExplore}>Explore courses <ArrowRight size={15} /></button>
		</div> : <div className="ai-workspace">
			<div className="ai-workspace-toolbar">
				<label htmlFor="ai-course-select">COURSE CONTEXT</label>
				<select id="ai-course-select" value={activeCourseId} onChange={(event) => { setSelectedCourseId(event.target.value); setMessages([]) }}>
					{availableCourses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
				</select>
				<span><Sparkles size={14} /> LangGraph learning workflow</span>
			</div>
			<div className="ai-message-list" aria-live="polite">
				{messages.length === 0 && <div className="ai-welcome">
					<span><Sparkles size={19} /></span>
					<h2>What are you learning today?</h2>
					<p>Ask a course question for a lesson-grounded answer, or request a study plan based on your completed lessons.</p>
				</div>}
				{messages.map((message, index) => <article className="ai-exchange" key={`${index}-${message.question}`}>
					<div className="ai-question"><span>You</span><p>{message.question}</p></div>
					<div className="ai-answer"><span><Sparkles size={14} /> {message.intent === 'study_plan' ? 'Student success agent' : 'Study assistant'}</span><p>{message.answer}</p>
						{message.sources.length > 0 && <div className="ai-sources"><strong>Course sources</strong>{message.sources.map((source) => <span key={source.lesson_id}><BookOpen size={13} /> {source.title}</span>)}</div>}
						{message.plan && <section className="ai-plan-card" aria-label="Suggested study plan">
							<header><div><strong>Suggested study plan</strong><small>{message.progress?.completed_lessons} of {message.progress?.total_lessons} lessons complete</small></div><span className={`ai-plan-status ai-plan-status-${message.plan.status}`}>{message.plan.status}</span></header>
							<p>{message.plan.rationale}</p>
							<ol>{message.plan.tasks.map((task, taskIndex) => <li key={`${task.lesson_id}-${taskIndex}`}><span><strong>{task.title}</strong><small>{task.description}</small></span><em>{task.estimated_minutes} min</em></li>)}</ol>
							{message.plan.status === 'pending' && <div className="ai-plan-actions">
								<button type="button" onClick={() => reviewPlan(message.plan.id, 'approve', index)} disabled={reviewingPlanId === message.plan.id}><Check size={14} /> Approve plan</button>
								<button type="button" onClick={() => reviewPlan(message.plan.id, 'reject', index)} disabled={reviewingPlanId === message.plan.id}><X size={14} /> Reject</button>
							</div>}
						</section>}
					</div>
				</article>)}
				{pending && <div className="ai-loading"><LoaderCircle size={16} /> Searching course lessons…</div>}
			</div>
			<form className="ai-question-form" onSubmit={submitQuestion}>
				{error && <p className="form-error" role="alert">{error}</p>}
				<div><textarea aria-label="Ask about this course" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a course question or request a study plan…" maxLength={2000} rows={2} disabled={pending} />
					<button className="primary-button" type="submit" aria-label="Send question" disabled={pending || question.trim().length < 5}><Send size={16} /></button></div>
				<small>Answers use enrolled-course lessons only. Verify important information with the cited material.</small>
			</form>
		</div>}
	</section>
}
