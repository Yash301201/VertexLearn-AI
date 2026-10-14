import { useState } from 'react'
import { ArrowRight, BookOpen, LoaderCircle, Send, Sparkles } from 'lucide-react'
import { api } from './lib/api'

export default function AIStudio({ courses, enrollments, session, onSignIn, onExplore }) {
	const [selectedCourseId, setSelectedCourseId] = useState('')
	const [question, setQuestion] = useState('')
	const [messages, setMessages] = useState([])
	const [error, setError] = useState('')
	const [pending, setPending] = useState(false)

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
			const response = await api('/ai/study', {
				method: 'POST',
				body: JSON.stringify({ course_id: Number(activeCourseId), question: submittedQuestion }),
			})
			setMessages((current) => [...current, {
				question: submittedQuestion,
				answer: response.answer,
				sources: response.sources,
			}])
		} catch (requestError) {
			setQuestion(submittedQuestion)
			setError(requestError.message)
		} finally {
			setPending(false)
		}
	}

	return <section className="view-section ai-studio-view">
		<div className="view-intro">
			<div className="eyebrow"><span className="eyebrow-dot" /> COURSE-GROUNDED PROJECT</div>
			<h1>AI study <span>assistant.</span></h1>
			<p>Ask about your course. Answers are grounded in its lessons and include sources to review.</p>
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
				<span><Sparkles size={14} /> Lesson-grounded answers</span>
			</div>
			<div className="ai-message-list" aria-live="polite">
				{messages.length === 0 && <div className="ai-welcome">
					<span><Sparkles size={19} /></span>
					<h2>What are you learning today?</h2>
					<p>Ask a specific question about this course. The assistant retrieves relevant lessons and cites them.</p>
				</div>}
				{messages.map((message, index) => <article className="ai-exchange" key={`${index}-${message.question}`}>
					<div className="ai-question"><span>You</span><p>{message.question}</p></div>
					<div className="ai-answer"><span><Sparkles size={14} /> Study assistant</span><p>{message.answer}</p>
						{message.sources.length > 0 && <div className="ai-sources"><strong>Course sources</strong>{message.sources.map((source) => <span key={source.lesson_id}><BookOpen size={13} /> {source.title}</span>)}</div>}
					</div>
				</article>)}
				{pending && <div className="ai-loading"><LoaderCircle size={16} /> Searching course lessons…</div>}
			</div>
			<form className="ai-question-form" onSubmit={submitQuestion}>
				{error && <p className="form-error" role="alert">{error}</p>}
				<div><textarea aria-label="Ask about this course" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about this course…" maxLength={2000} rows={2} disabled={pending} />
					<button className="primary-button" type="submit" aria-label="Send question" disabled={pending || question.trim().length < 5}><Send size={16} /></button></div>
				<small>Answers use enrolled-course lessons only. Verify important information with the cited material.</small>
			</form>
		</div>}
	</section>
}
