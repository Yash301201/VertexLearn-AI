import { useEffect, useState } from 'react'
import { BookOpen, Plus, ShieldCheck } from 'lucide-react'
import { api } from './lib/api'

const emptyCourse = { title: '', description: '', instructor: '' }
const emptyLesson = { title: '', content: '' }

export default function AdminPanel({ onNotice }) {
  const [courses, setCourses] = useState([])
  const [courseForm, setCourseForm] = useState(emptyCourse)
  const [lessonForm, setLessonForm] = useState(emptyLesson)
  const [lessonCourseId, setLessonCourseId] = useState(null)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function refreshCourses() {
    setLoading(true)
    setError('')
    try {
      const data = await api('/courses/')
      const courseRows = await Promise.all((data.courses ?? []).map(async (course) => {
        const lessonData = await api(`/courses/${course.id}/lessons`)
        return { ...course, lesson_count: lessonData.lessons?.length ?? 0 }
      }))
      setCourses(courseRows)
    } catch (loadError) {
      setError(loadError.message || 'Could not load courses.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshCourses()
  }, [])

  async function createCourse(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api('/courses/', {
        method: 'POST',
        body: JSON.stringify(courseForm),
      })
      setCourseForm(emptyCourse)
      onNotice('Course created.')
      await refreshCourses()
    } catch (submitError) {
      setError(submitError.message || 'Could not create this course.')
    } finally {
      setBusy(false)
    }
  }

  async function createLesson(event, courseId) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api(`/courses/${courseId}/lessons`, {
        method: 'POST',
        body: JSON.stringify(lessonForm),
      })
      setLessonForm(emptyLesson)
      setLessonCourseId(null)
      onNotice('Lesson added to course.')
      await refreshCourses()
    } catch (submitError) {
      setError(submitError.message || 'Could not add this lesson.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="view-section admin-view">
      <div className="view-intro">
        <div className="eyebrow"><span className="eyebrow-dot" /> ADMINISTRATION</div>
        <h1>Build your <span>classroom.</span></h1>
        <p>Create courses and organize their lessons.</p>
      </div>

      <div className="admin-summary" aria-label="Content summary">
        <article><span>COURSES</span><strong>{courses.length.toString().padStart(2, '0')}</strong></article>
        <article><span>LESSONS</span><strong>{courses.reduce((total, course) => total + course.lesson_count, 0).toString().padStart(2, '0')}</strong></article>
        <article><span>ACCESS</span><strong><ShieldCheck size={20} /> Admin</strong></article>
      </div>

      <div className="admin-workspace">
        <section className="admin-section">
          <div className="section-heading">
            <div><span className="section-kicker">COURSE CATALOG</span><h2>Create a course</h2></div>
          </div>
          <form className="admin-form" onSubmit={createCourse}>
            <label>Course title<input required minLength={3} maxLength={200} value={courseForm.title} onChange={(event) => setCourseForm({ ...courseForm, title: event.target.value })} placeholder="e.g. Python Programming" /></label>
            <label>Instructor<input required minLength={2} maxLength={100} value={courseForm.instructor} onChange={(event) => setCourseForm({ ...courseForm, instructor: event.target.value })} placeholder="Instructor name" /></label>
            <label className="admin-form-wide">Description<textarea required minLength={10} maxLength={2000} rows={4} value={courseForm.description} onChange={(event) => setCourseForm({ ...courseForm, description: event.target.value })} placeholder="What will learners study?" /></label>
            {error && <p className="admin-error" role="alert">{error}</p>}
            <button className="primary-button" disabled={busy}><Plus size={16} />{busy ? 'Saving…' : 'Create course'}</button>
          </form>
        </section>

        <section className="admin-section">
          <div className="section-heading">
            <div><span className="section-kicker">YOUR CONTENT</span><h2>Courses and lessons</h2></div>
            <button className="text-action" onClick={refreshCourses}>Refresh</button>
          </div>
          {loading ? <div className="admin-loading">Loading courses…</div> : courses.length === 0 ? (
            <div className="admin-empty"><BookOpen size={20} /><strong>No courses yet</strong><span>Create your first course to start building lessons.</span></div>
          ) : (
            <div className="admin-course-list">
              {courses.map((course, index) => (
                <article className="admin-course-row" key={course.id}>
                  <span className="admin-course-number">{String(index + 1).padStart(2, '0')}</span>
                  <div className="admin-course-copy">
                    <h3>{course.title}</h3>
                    <p>{course.instructor} <i>·</i> {course.lesson_count} {course.lesson_count === 1 ? 'lesson' : 'lessons'}</p>
                    <span>{course.description}</span>
                  </div>
                  <button className="admin-add-lesson" aria-expanded={lessonCourseId === course.id} onClick={() => { setLessonCourseId(lessonCourseId === course.id ? null : course.id); setLessonForm(emptyLesson); setError('') }}>
                    <Plus size={15} /> Add lesson
                  </button>
                  {lessonCourseId === course.id && (
                    <form className="admin-lesson-form" onSubmit={(event) => createLesson(event, course.id)}>
                      <label>Lesson title<input required minLength={3} maxLength={200} value={lessonForm.title} onChange={(event) => setLessonForm({ ...lessonForm, title: event.target.value })} placeholder="e.g. Python basics" /></label>
                      <label>Lesson content<textarea required maxLength={20000} rows={3} value={lessonForm.content} onChange={(event) => setLessonForm({ ...lessonForm, content: event.target.value })} placeholder="Write the lesson content" /></label>
                      <button className="primary-button" disabled={busy}>{busy ? 'Saving…' : 'Save lesson'}</button>
                    </form>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </section>
  )
}