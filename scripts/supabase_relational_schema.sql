CREATE SCHEMA IF NOT EXISTS lms;

CREATE TABLE IF NOT EXISTS lms.classes (
  id text PRIMARY KEY,
  name text NOT NULL,
  status text,
  course text,
  centre text,
  block text,
  level text,
  sessions integer,
  studentcount integer DEFAULT 0,
  attendedcount integer DEFAULT 0,
  completedcount integer DEFAULT 0,
  completionrate integer DEFAULT 0,
  commentpercentage integer DEFAULT 0,
  totalslotswithstudents integer DEFAULT 0,
  slotswithfullcomments integer DEFAULT 0,
  startdate text,
  enddate text,
  createdat text,
  updatedat timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lms.class_teachers (
  id bigint PRIMARY KEY,
  classid text NOT NULL,
  name text,
  email text,
  role text
);

CREATE TABLE IF NOT EXISTS lms.slots (
  id text PRIMARY KEY,
  classid text NOT NULL,
  date text,
  starttime text,
  endtime text,
  commentstatus text,
  studentsinslot integer DEFAULT 0,
  studentswithcomment integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lms.slot_comments (
  id text PRIMARY KEY,
  classid text NOT NULL,
  slotid text NOT NULL,
  sessionindex integer,
  slotdate text,
  studentid text,
  studentname text,
  comment text,
  sendcommentstatus text
);

CREATE TABLE IF NOT EXISTS lms.slot_students (
  id bigint PRIMARY KEY,
  classid text NOT NULL,
  slotid text NOT NULL,
  studentid text,
  studentname text,
  status text
);

CREATE TABLE IF NOT EXISTS lms.class_students (
  id text PRIMARY KEY,
  classid text NOT NULL,
  studentid text,
  activeinclass integer DEFAULT 0,
  completed integer DEFAULT 0,
  attended integer DEFAULT 0,
  note text,
  grade text,
  retentiondate text,
  completioninfo text,
  student text,
  previousclass text
);

CREATE TABLE IF NOT EXISTS lms.incomplete_students (
  id bigint PRIMARY KEY,
  classid text NOT NULL,
  name text
);

CREATE TABLE IF NOT EXISTS lms.teachers (
  id text PRIMARY KEY,
  fullname text,
  code text,
  username text,
  email text,
  personalemail text,
  phonenumber text,
  gender text,
  dob text,
  address text,
  isactive integer DEFAULT 1,
  teacherpoint real DEFAULT 0,
  joineddate text,
  updatedat timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lms.teacher_centres (
  id bigint PRIMARY KEY,
  teacherid text NOT NULL,
  centre text
);

CREATE TABLE IF NOT EXISTS lms.teacher_blocks (
  id bigint PRIMARY KEY,
  teacherid text NOT NULL,
  block text
);

CREATE TABLE IF NOT EXISTS lms.teacher_course_lines (
  id bigint PRIMARY KEY,
  teacherid text NOT NULL,
  courseline text
);

CREATE TABLE IF NOT EXISTS lms.tp_records (
  classid text PRIMARY KEY,
  classname text,
  centre text,
  block text,
  tp1 real,
  tp2 real,
  updatedat timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lms.tp_students (
  id bigint PRIMARY KEY,
  classid text NOT NULL,
  round integer NOT NULL,
  name text,
  score real,
  textanswers text
);

CREATE TABLE IF NOT EXISTS lms.tp_teachers (
  id bigint PRIMARY KEY,
  classid text NOT NULL,
  name text,
  email text,
  role text
);

CREATE TABLE IF NOT EXISTS lms.cp_records (
  classid text PRIMARY KEY,
  classname text,
  centre text,
  block text,
  cp1theory real,
  cp1practical real,
  cp2theory real,
  cp2practical real,
  updatedat timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lms.cp_students (
  id bigint PRIMARY KEY,
  classid text NOT NULL,
  round integer NOT NULL,
  name text,
  theoryscore real,
  practicalscore real
);

CREATE TABLE IF NOT EXISTS lms.cp_teachers (
  id bigint PRIMARY KEY,
  classid text NOT NULL,
  name text,
  email text,
  role text
);

CREATE TABLE IF NOT EXISTS lms.assignment_records (
  classid text PRIMARY KEY,
  classname text,
  centre text,
  block text,
  status text,
  updatedat timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lms.assignment_students (
  id text,
  classid text NOT NULL,
  displayname text,
  studentuid text,
  PRIMARY KEY (classid, studentuid)
);

CREATE TABLE IF NOT EXISTS lms.assignment_lessons (
  id text,
  classid text NOT NULL,
  name text,
  type text,
  isactive integer DEFAULT 0,
  learningcourseid text,
  displayorder integer,
  PRIMARY KEY (classid, id)
);

CREATE TABLE IF NOT EXISTS lms.assignment_submissions (
  id text PRIMARY KEY,
  classid text NOT NULL,
  type text,
  note text,
  score real,
  status text,
  category text,
  lessonid text,
  learningcourseid text,
  studentuid text,
  studentoriginalid text,
  classsessionid text,
  markedat text,
  markedby text,
  createdat text,
  submittedat text,
  submittedcount integer DEFAULT 0,
  contentjson text
);

CREATE TABLE IF NOT EXISTS lms.assignment_teachers (
  id bigint PRIMARY KEY,
  classid text NOT NULL,
  name text,
  email text,
  role text
);

CREATE TABLE IF NOT EXISTS lms.assignment_fetch_errors (
  classid text PRIMARY KEY,
  classname text,
  centre text,
  block text,
  status text,
  errortype text,
  message text,
  fetchedat timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lms.oh_records (
  id text PRIMARY KEY,
  starttime text,
  endtime text,
  status text,
  centreid text,
  centrename text,
  centreshortname text,
  teacherid text,
  teacherfullname text,
  teacherusername text,
  teacheremail text,
  note text,
  managernote text,
  type text,
  studentcount integer DEFAULT 0,
  createdbyusername text,
  createdat text,
  updatedat timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lms.oh_courses (
  id bigint PRIMARY KEY,
  ohid text NOT NULL,
  courseid text,
  coursename text,
  shortname text
);

CREATE TABLE IF NOT EXISTS lms.oh_course_lines (
  id bigint PRIMARY KEY,
  ohid text NOT NULL,
  courselineid text,
  courselinename text
);

CREATE TABLE IF NOT EXISTS lms.oh_appointments (
  id text PRIMARY KEY,
  ohid text NOT NULL,
  title text,
  candidateid text,
  candidatename text,
  status text,
  note text
);

CREATE TABLE IF NOT EXISTS lms.oh_appointment_courses (
  id bigint PRIMARY KEY,
  appointmentid text NOT NULL,
  courseid text,
  coursename text,
  shortname text
);

CREATE INDEX IF NOT EXISTS idx_lms_classes_status ON lms.classes(status);
CREATE INDEX IF NOT EXISTS idx_lms_classes_centre ON lms.classes(centre);
CREATE INDEX IF NOT EXISTS idx_lms_classes_block ON lms.classes(block);
CREATE INDEX IF NOT EXISTS idx_lms_classes_createdat ON lms.classes(createdat DESC);
CREATE INDEX IF NOT EXISTS idx_lms_class_teachers_classid ON lms.class_teachers(classid);
CREATE INDEX IF NOT EXISTS idx_lms_slots_classid ON lms.slots(classid);
CREATE INDEX IF NOT EXISTS idx_lms_slot_comments_classid ON lms.slot_comments(classid);
CREATE INDEX IF NOT EXISTS idx_lms_slot_comments_slotid ON lms.slot_comments(slotid);
CREATE INDEX IF NOT EXISTS idx_lms_slot_students_classid ON lms.slot_students(classid);
CREATE INDEX IF NOT EXISTS idx_lms_slot_students_slotid ON lms.slot_students(slotid);
CREATE INDEX IF NOT EXISTS idx_lms_class_students_classid ON lms.class_students(classid);
CREATE INDEX IF NOT EXISTS idx_lms_class_students_studentid ON lms.class_students(studentid);
CREATE INDEX IF NOT EXISTS idx_lms_teacher_centres_teacherid ON lms.teacher_centres(teacherid);
CREATE INDEX IF NOT EXISTS idx_lms_teacher_blocks_teacherid ON lms.teacher_blocks(teacherid);
CREATE INDEX IF NOT EXISTS idx_lms_teacher_course_lines_teacherid ON lms.teacher_course_lines(teacherid);
CREATE INDEX IF NOT EXISTS idx_lms_tp_students_classid ON lms.tp_students(classid);
CREATE INDEX IF NOT EXISTS idx_lms_tp_teachers_classid ON lms.tp_teachers(classid);
CREATE INDEX IF NOT EXISTS idx_lms_cp_students_classid ON lms.cp_students(classid);
CREATE INDEX IF NOT EXISTS idx_lms_cp_teachers_classid ON lms.cp_teachers(classid);
CREATE INDEX IF NOT EXISTS idx_lms_assignment_students_classid ON lms.assignment_students(classid);
CREATE INDEX IF NOT EXISTS idx_lms_assignment_lessons_classid ON lms.assignment_lessons(classid);
CREATE INDEX IF NOT EXISTS idx_lms_assignment_submissions_classid ON lms.assignment_submissions(classid);
CREATE INDEX IF NOT EXISTS idx_lms_assignment_submissions_lessonid ON lms.assignment_submissions(lessonid);
CREATE INDEX IF NOT EXISTS idx_lms_assignment_submissions_studentuid ON lms.assignment_submissions(studentuid);
CREATE INDEX IF NOT EXISTS idx_lms_assignment_teachers_classid ON lms.assignment_teachers(classid);
CREATE INDEX IF NOT EXISTS idx_lms_oh_centre ON lms.oh_records(centreid);
CREATE INDEX IF NOT EXISTS idx_lms_oh_starttime ON lms.oh_records(starttime);
CREATE INDEX IF NOT EXISTS idx_lms_oh_courses_ohid ON lms.oh_courses(ohid);
CREATE INDEX IF NOT EXISTS idx_lms_oh_course_lines_ohid ON lms.oh_course_lines(ohid);
CREATE INDEX IF NOT EXISTS idx_lms_oh_appt_ohid ON lms.oh_appointments(ohid);
CREATE INDEX IF NOT EXISTS idx_lms_oh_appointment_courses_appointmentid ON lms.oh_appointment_courses(appointmentid);

REVOKE ALL ON SCHEMA lms FROM anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA lms FROM anon, authenticated;
