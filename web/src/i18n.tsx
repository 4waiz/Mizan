import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type Lang = "en" | "ar";

const T: Record<string, { en: string; ar: string }> = {
  app_title: { en: "Mizan - Arrears Rescheduling", ar: "ميزان - إعادة جدولة المتأخرات" },
  subtitle: {
    en: "Sheikh Zayed Housing Programme · MOEI",
    ar: "برنامج الشيخ زايد للإسكان · وزارة الطاقة والبنية التحتية",
  },
  login: { en: "Sign in with UAE PASS", ar: "تسجيل الدخول عبر الهوية الرقمية" },
  beneficiary: { en: "Beneficiary", ar: "المستفيد" },
  officer: { en: "Officer", ar: "الموظف" },
  insight: { en: "Insight", ar: "التحليلات" },
  home: { en: "Home", ar: "الرئيسية" },
  new_request: { en: "New Rescheduling Request", ar: "طلب إعادة جدولة جديد" },
  my_case: { en: "My Case", ar: "حالتي" },
  profile: { en: "Beneficiary Profile", ar: "ملف المستفيد" },
  documents: { en: "Documents", ar: "المستندات" },
  validation: { en: "Validation", ar: "التحقق" },
  recommendation: { en: "Recommendation", ar: "التوصية" },
  status: { en: "Case Status", ar: "حالة الطلب" },
  queue: { en: "Review Queue", ar: "قائمة المراجعة" },
  confidence: { en: "Confidence", ar: "درجة الثقة" },
  risk: { en: "Re-default risk", ar: "مخاطر التعثر" },
  income: { en: "Monthly income", ar: "الدخل الشهري" },
  installment: { en: "Installment", ar: "القسط" },
  arrears: { en: "Arrears", ar: "المتأخرات" },
  approve: { en: "Approve", ar: "اعتماد" },
  override: { en: "Override", ar: "تعديل/تجاوز" },
  reject: { en: "Reject", ar: "رفض" },
  notes: { en: "Decision notes", ar: "ملاحظات القرار" },
  submit: { en: "Submit request", ar: "إرسال الطلب" },
  run: { en: "Run assessment", ar: "تشغيل التقييم" },
  escalation: { en: "Escalation reason", ar: "سبب الإحالة" },
  policy_checks: { en: "Policy checks", ar: "فحوصات السياسة" },
  candidate_plans: { en: "Candidate plans", ar: "الخطط المقترحة" },
  evidence: { en: "Evidence", ar: "الأدلة" },
  audit: { en: "Audit trail", ar: "سجل التدقيق" },
  proactive: { en: "Proactive Alerts", ar: "التنبيهات الاستباقية" },
  replay: { en: "Replay Dashboard", ar: "لوحة الإعادة" },
  language: { en: "Language", ar: "اللغة" },
  high_contrast: { en: "High-contrast mode", ar: "وضع التباين العالي" },
  signed_in_as: { en: "Signed in as", ar: "تم تسجيل الدخول باسم" },

  // ── Authentication / login (referenced by CitizenLogin & OfficerLogin) ─────
  username: { en: "Username", ar: "اسم المستخدم" },
  password: { en: "Password", ar: "كلمة المرور" },
  sign_in: { en: "Sign in", ar: "تسجيل الدخول" },
  citizen_portal: { en: "Citizen Portal", ar: "بوابة المستفيد" },
  citizen_login_lead: {
    en: "Sign in to submit a rescheduling request and track its determination.",
    ar: "سجّل الدخول لتقديم طلب إعادة جدولة ومتابعة قراره.",
  },
  backend_unreachable: {
    en: "The service is currently unreachable. Please try again shortly.",
    ar: "الخدمة غير متاحة حالياً. يُرجى المحاولة مرة أخرى بعد قليل.",
  },
  account: { en: "Account", ar: "الحساب" },
  authentication: { en: "Authentication", ar: "التحقق من الهوية" },
  citizen_identity_uaepass: {
    en: "Choose the identity to authenticate with UAE PASS",
    ar: "اختر الهوية للمصادقة عبر الهوية الرقمية",
  },
  are_you_officer: { en: "Are you an officer?", ar: "هل أنت موظف؟" },
  officer_dashboard_signin: {
    en: "Sign in to the Officer Dashboard",
    ar: "تسجيل الدخول إلى لوحة الموظف",
  },
  identity_unavailable: {
    en: "Selected identity is unavailable.",
    ar: "الهوية المختارة غير متاحة.",
  },
  invalid_credentials: {
    en: "Invalid username or password.",
    ar: "اسم المستخدم أو كلمة المرور غير صحيحة.",
  },
  invalid_officer_credentials: {
    en: "Invalid officer credentials.",
    ar: "بيانات اعتماد الموظف غير صحيحة.",
  },
  officer_dashboard: { en: "Officer Dashboard", ar: "لوحة الموظف" },
  officer_login_lead: {
    en: "Sign in to review escalated cases and issue determinations.",
    ar: "سجّل الدخول لمراجعة الحالات المُحالة وإصدار القرارات.",
  },
  officer_authentication: { en: "Officer authentication", ar: "مصادقة الموظف" },
  sign_in_dashboard: { en: "Sign in to dashboard", ar: "تسجيل الدخول إلى اللوحة" },
  not_an_officer: { en: "Not an officer?", ar: "لست موظفاً؟" },
  citizen_portal_signin: { en: "Citizen Portal sign-in", ar: "تسجيل الدخول لبوابة المستفيد" },

  // ── Historical Intelligence / Insights ─────────────────────────────────────
  insights: { en: "Historical Intelligence", ar: "الذكاء التاريخي" },
  rationale_placeholder: {
    en: "Rationale for your decision…",
    ar: "مبررات قرارك…",
  },

  // ── Home page ──────────────────────────────────────────────────────────────
  home_band_title: { en: "An autonomous case officer", ar: "موظف حالات ذاتي القيادة" },
  home_lead_pre: { en: "Mizan turns the manual", ar: "يحوّل ميزان مراجعة إعادة جدولة المتأخرات اليدوية التي تستغرق" },
  home_lead_days: { en: "five-working-day", ar: "خمسة أيام عمل" },
  home_lead_mid: { en: "arrears rescheduling review into an", ar: "إلى قرار" },
  home_lead_attrs: { en: "instant, explainable, auditable", ar: "فوري وقابل للتفسير والتدقيق" },
  home_lead_post: {
    en: "decision - escalating only the exceptional cases to a human.",
    ar: "— مع إحالة الحالات الاستثنائية فقط إلى موظف بشري.",
  },
  signed_in_role_citizen: { en: "Citizen", ar: "مستفيد" },
  signed_in_role_officer: { en: "Officer", ar: "موظف" },
  go_to_portal: { en: "Go to your portal →", ar: "اذهب إلى بوابتك ←" },
  go_to_dashboard: { en: "Go to your dashboard →", ar: "اذهب إلى لوحتك ←" },
  skip_intro: { en: "Skip intro →", ar: "تخطّي المقدمة ←" },
  choose_your_portal: { en: "Choose your portal", ar: "اختر بوابتك" },
  citizen_portal_card_t1: { en: "Sign in with your account or UAE PASS", ar: "سجّل الدخول بحسابك أو عبر الهوية الرقمية" },
  citizen_portal_card_t2: { en: "Submit a rescheduling request", ar: "قدّم طلب إعادة جدولة" },
  citizen_portal_card_t3: { en: "Watch the assessment run, step by step", ar: "تابع تنفيذ التقييم خطوة بخطوة" },
  citizen_portal_card_t4: { en: "Track the decision on My Case", ar: "تابع القرار في صفحة حالتي" },
  citizen_signin_btn: { en: "Citizen sign-in →", ar: "تسجيل دخول المستفيد ←" },
  officer_dashboard_card_t1: { en: "Review the escalation queue", ar: "راجع قائمة الإحالات" },
  officer_dashboard_card_t2: { en: "Approve, override or reject determinations", ar: "اعتمد أو عدّل أو ارفض القرارات" },
  officer_dashboard_card_t3: { en: "Proactive risk alerts", ar: "تنبيهات المخاطر الاستباقية" },
  officer_dashboard_card_t4: { en: "Replay & audit dashboard", ar: "لوحة الإعادة والتدقيق" },
  officer_signin_btn: { en: "Officer sign-in →", ar: "تسجيل دخول الموظف ←" },
  how_it_works: { en: "How it works", ar: "كيف يعمل" },
  hiw_citizen_i1: { en: "New Request", ar: "طلب جديد" },
  hiw_citizen_i2: { en: "My Case · status + result", ar: "حالتي · الحالة والنتيجة" },
  hiw_officer_i1: { en: "Review Queue", ar: "قائمة المراجعة" },
  hiw_officer_i2: { en: "Case detail + actions", ar: "تفاصيل الحالة والإجراءات" },
  hiw_insight_i1: { en: "Proactive Alerts", ar: "التنبيهات الاستباقية" },
  hiw_insight_i2: { en: "Replay Dashboard", ar: "لوحة الإعادة" },

  // ── NewRequest page ────────────────────────────────────────────────────────
  please_signin_citizen_pre: { en: "Please", ar: "يُرجى" },
  please_signin_citizen_link: { en: "sign in to the Citizen Portal", ar: "تسجيل الدخول إلى بوابة المستفيد" },
  please_signin_citizen_post: { en: "first.", ar: "أولاً." },
  identity_autofill_note: {
    en: "Identity auto-filled from UAE PASS. Financial figures are revealed once your supporting documents are uploaded and verified below.",
    ar: "تُعبّأ الهوية تلقائياً من الهوية الرقمية. تُكشف الأرقام المالية بمجرد رفع مستنداتك الداعمة والتحقق منها أدناه.",
  },
  start_new_application: { en: "↺ Start new application", ar: "↺ بدء طلب جديد" },
  start_new_application_title: {
    en: "Discard uploads and begin a fresh application",
    ar: "تجاهل الملفات المرفوعة وابدأ طلباً جديداً",
  },
  required_documents: { en: "Required documents", ar: "المستندات المطلوبة" },
  not_uploaded: { en: " · not uploaded", ar: " · لم يُرفع" },
  uploading: { en: "Uploading…", ar: "جارٍ الرفع…" },
  dragdrop_documents: { en: "Drag & drop all your documents here", ar: "اسحب وأفلت جميع مستنداتك هنا" },
  dragdrop_hint: {
    en: "or click to browse — you can select multiple files at once (PDF, PNG, JPG)",
    ar: "أو انقر للتصفح — يمكنك اختيار عدة ملفات دفعة واحدة (PDF، PNG، JPG)",
  },
  no_documents_yet: { en: "No documents uploaded yet.", ar: "لم تُرفع أي مستندات بعد." },
  submit_and_assess: { en: "Submit & assess", ar: "الإرسال والتقييم" },
  pipeline_explainer: {
    en: "Submitting runs the governed pipeline: document audit → fraud/dedupe → affordability → risk → policy solver → human-review gate. A duplicate or active application is rejected immediately at the fraud/dedupe step.",
    ar: "يؤدي الإرسال إلى تشغيل المسار المُنظَّم: تدقيق المستندات ← الاحتيال/إزالة التكرار ← القدرة على السداد ← المخاطر ← محرّك السياسات ← بوابة المراجعة البشرية. يُرفض أي طلب مكرر أو نشط فوراً عند خطوة الاحتيال/إزالة التكرار.",
  },
  some_documents_missing: { en: "Some documents still appear to be missing:", ar: "لا تزال بعض المستندات مفقودة على ما يبدو:" },
  assessment_complete: { en: "Assessment complete.", ar: "اكتمل التقييم." },
  processing_time: { en: "Processing time", ar: "زمن المعالجة" },
  view_full_result: { en: "➡ View full result on My Case", ar: "➡ عرض النتيجة الكاملة في حالتي" },
  additional_info_required: { en: "Additional information required.", ar: "مطلوب معلومات إضافية." },
  skipped_incomplete_note: {
    en: "Affordability and risk analysis were skipped: no decision is made on an incomplete application until the missing documents are provided.",
    ar: "تم تخطّي تحليل القدرة على السداد والمخاطر: لا يُتخذ قرار بشأن طلب غير مكتمل حتى تُقدَّم المستندات الناقصة.",
  },
  assessment_failed_rejected: { en: "Assessment failed — request rejected.", ar: "فشل التقييم — رُفض الطلب." },
  skipped_duplicate_note: {
    en: "Affordability and risk analysis were skipped: there is no point assessing a duplicate request.",
    ar: "تم تخطّي تحليل القدرة على السداد والمخاطر: لا جدوى من تقييم طلب مكرر.",
  },

  // Document type labels (NewRequest checklist + uploaded files)
  doc_emirates_id: { en: "Emirates ID", ar: "الهوية الإماراتية" },
  doc_salary_certificate: { en: "Salary certificate", ar: "شهادة راتب" },
  doc_bank_statement: { en: "Bank statement", ar: "كشف حساب بنكي" },
  doc_liability_letter: { en: "Financial obligations letter", ar: "خطاب الالتزامات المالية" },
  doc_termination_letter: { en: "Termination / unemployment letter", ar: "خطاب إنهاء الخدمة / البطالة" },
  doc_medical_report: { en: "Medical report", ar: "تقرير طبي" },
  doc_hardship_letter: { en: "Hardship letter", ar: "خطاب إثبات الضائقة" },
  doc_unknown: { en: "Document", ar: "مستند" },

  // ── MyCase page ────────────────────────────────────────────────────────────
  case_id: { en: "Case ID", ar: "رقم الحالة" },
  load: { en: "Load", ar: "تحميل" },
  submit_or_paste_case: { en: "Submit a request first, or paste a case ID.", ar: "قدّم طلباً أولاً، أو الصق رقم الحالة." },
  not_assessed_pre: {
    en: "This application hasn’t been assessed yet. Upload your documents and run the assessment on",
    ar: "لم يُقيَّم هذا الطلب بعد. ارفع مستنداتك وشغّل التقييم في",
  },
  not_assessed_post: {
    en: "— the decision, plans and financials appear here once the AI pipeline has read your documents.",
    ar: "— يظهر القرار والخطط والبيانات المالية هنا بمجرد أن يقرأ المسار الذكي مستنداتك.",
  },
  decided_in: { en: "Decided in", ar: "تم القرار خلال" },
  legacy_sla_label: { en: "legacy SLA:", ar: "اتفاقية الخدمة السابقة:" },
  working_days: { en: "working days", ar: "أيام عمل" },

  // ── OfficerQueue page ──────────────────────────────────────────────────────
  queue_subtitle: { en: "Officer · cases escalated for human review", ar: "الموظف · حالات مُحالة للمراجعة البشرية" },
  queue_count_suffix: { en: "case(s) escalated · awaiting determination", ar: "حالة مُحالة · بانتظار القرار" },
  queue_empty: {
    en: "Queue is empty - all recent cases were handled straight-through.",
    ar: "القائمة فارغة — جميع الحالات الأخيرة عُولجت آلياً دون تدخل.",
  },
  open_arrow: { en: "Open →", ar: "فتح ←" },

  // ── OfficerCase page ───────────────────────────────────────────────────────
  case_review: { en: "Case Review", ar: "مراجعة الحالة" },
  case_review_subtitle: { en: "Officer · evidence, policy & determination", ar: "الموظف · الأدلة والسياسة والقرار" },
  officer_id: { en: "Officer ID", ar: "رقم الموظف" },
  open_from_queue: { en: "Open a case from the Review Queue.", ar: "افتح حالة من قائمة المراجعة." },
  decision: { en: "Decision", ar: "القرار" },
  approved_logged: { en: "Approved. Logged to the audit trail.", ar: "تم الاعتماد. سُجّل في سجل التدقيق." },
  rejected_logged: { en: "Rejected. Logged to the audit trail.", ar: "تم الرفض. سُجّل في سجل التدقيق." },
  override_applied: { en: "Override applied.", ar: "تم تطبيق التعديل." },
  new_outcome: { en: "New outcome", ar: "نتيجة جديدة" },
  new_installment_aed: { en: "New installment (AED)", ar: "القسط الجديد (درهم)" },
  new_term_months: { en: "New term (months)", ar: "المدة الجديدة (أشهر)" },
  apply_override: { en: "Apply override", ar: "تطبيق التعديل" },
  last_action: { en: "Last action:", ar: "آخر إجراء:" },
  extracted_prefix: { en: "Extracted:", ar: "مُستخرَج:" },
  fraud_flags_prefix: { en: "Fraud flags:", ar: "علامات الاحتيال:" },
  no_extracted_text: { en: "(no extracted text)", ar: "(لا يوجد نص مُستخرَج)" },

  // ── Replay page ────────────────────────────────────────────────────────────
  replay_dashboard: { en: "Replay Dashboard", ar: "لوحة الإعادة" },
  replay_subtitle: { en: "Consistency & impact across all cases", ar: "الاتساق والأثر عبر جميع الحالات" },
  loading: { en: "Loading…", ar: "جارٍ التحميل…" },
  total_cases: { en: "Total cases", ar: "إجمالي الحالات" },
  straight_through: { en: "Straight-through", ar: "معالجة آلية مباشرة" },
  human_review: { en: "Human review", ar: "مراجعة بشرية" },
  manual_days_saved: { en: "Manual days saved", ar: "أيام العمل اليدوي الموفّرة" },
  avg_processing_pre: { en: "Average automated processing time:", ar: "متوسط زمن المعالجة الآلية:" },
  avg_processing_sla: { en: "legacy SLA:", ar: "اتفاقية الخدمة السابقة:" },
  per_case: { en: "working days per case.", ar: "أيام عمل لكل حالة." },
  outcomes: { en: "Outcomes", ar: "النتائج" },
  cases: { en: "Cases", ar: "الحالات" },

  // ── Proactive page ─────────────────────────────────────────────────────────
  proactive_subtitle: { en: "Insight · early-warning watchlist", ar: "تحليلات · قائمة الإنذار المبكر" },
  proactive_lead_pre: { en: "Cases flagged", ar: "حالات مُعلَّمة" },
  proactive_lead_before: { en: "before", ar: "قبل" },
  proactive_lead_post: {
    en: "they fall into serious arrears, ranked by re-default risk - enabling early officer outreach.",
    ar: "أن تتحوّل إلى متأخرات خطيرة، مرتّبة حسب مخاطر التعثر — لتمكين التواصل المبكر من الموظف.",
  },
  no_proactive_alerts: { en: "No proactive alerts at present.", ar: "لا توجد تنبيهات استباقية حالياً." },
  drivers_prefix: { en: "Drivers:", ar: "المحركات:" },
  suggested_action_prefix: { en: "Suggested action:", ar: "الإجراء المقترح:" },
  open_case_arrow: { en: "Open case →", ar: "فتح الحالة ←" },

  // ── Layout / shell ─────────────────────────────────────────────────────────
  nav_case_review: { en: "Case Review", ar: "مراجعة الحالة" },
  service_unavailable: { en: "Service unavailable", ar: "الخدمة غير متاحة" },
  all_systems_operational: { en: "All systems operational", ar: "جميع الأنظمة تعمل" },
  offline: { en: "Offline", ar: "غير متصل" },
  system_online: { en: "System online", ar: "النظام متصل" },
  citizen_session: { en: "Citizen session", ar: "جلسة مستفيد" },
  officer_session: { en: "Officer session", ar: "جلسة موظف" },
  sign_out: { en: "Sign out", ar: "تسجيل الخروج" },
  go_to_home: { en: "Go to home", ar: "الذهاب إلى الرئيسية" },
  brand_sub: {
    en: "Sheikh Zayed Housing Programme · MOEI. An autonomous case officer for arrears rescheduling.",
    ar: "برنامج الشيخ زايد للإسكان · وزارة الطاقة والبنية التحتية. موظف حالات ذاتي القيادة لإعادة جدولة المتأخرات.",
  },
  footer_signed_in: { en: "Signed in ·", ar: "مُسجّل الدخول ·" },

  // ── ErrorBoundary ──────────────────────────────────────────────────────────
  ui_error_title: { en: "The UI hit an error", ar: "واجهت الواجهة خطأً" },
  clear_session_reload: { en: "Clear session & reload", ar: "مسح الجلسة وإعادة التحميل" },

  // ── Historical Intelligence dashboard (Insights) ───────────────────────────
  insights_subtitle: {
    en: "Insight · organizer historical dataset",
    ar: "تحليلات · مجموعة البيانات التاريخية للمنظِّم",
  },
  insights_lead: {
    en: "Aggregated evidence from the organizer's historical arrears-rescheduling records — used to calibrate proactive risk scoring and validate policy edge cases.",
    ar: "أدلة مجمّعة من السجلات التاريخية لإعادة جدولة المتأخرات لدى المنظِّم — تُستخدم لمعايرة تسجيل المخاطر الاستباقي والتحقق من حالات السياسة الحدية.",
  },
  insights_dataset_missing_title: { en: "Historical dataset not loaded", ar: "لم تُحمَّل مجموعة البيانات التاريخية" },
  insights_dataset_missing_hint: {
    en: "Place the historical workbook at data/RescheduleArrears.xlsx and restart the backend to enable this dashboard.",
    ar: "ضع ملف البيانات التاريخي في data/RescheduleArrears.xlsx وأعد تشغيل الخادم لتفعيل هذه اللوحة.",
  },
  insights_kpis: { en: "Dataset at a glance", ar: "نظرة سريعة على البيانات" },
  kpi_total_cases: { en: "Total historical cases analyzed", ar: "إجمالي الحالات التاريخية المُحلَّلة" },
  kpi_usable_records: { en: "Usable records", ar: "السجلات القابلة للاستخدام" },
  kpi_years_covered: { en: "Years covered", ar: "السنوات المشمولة" },
  kpi_median_overdue_amt: { en: "Median overdue amount", ar: "الوسيط لمبلغ المتأخرات" },
  kpi_median_overdue_months: { en: "Median overdue months", ar: "الوسيط لأشهر المتأخرات" },
  kpi_median_salary: { en: "Median salary", ar: "الوسيط للراتب" },
  kpi_median_current_emi: { en: "Median current installment", ar: "الوسيط للقسط الحالي" },
  months_suffix: { en: "months", ar: "أشهر" },
  insights_request_split: { en: "Request-type split", ar: "توزيع نوع الطلب" },
  insights_risk_buckets: { en: "Overdue-month risk buckets", ar: "فئات مخاطر أشهر التأخر" },
  insights_cap_edge: { en: "20% deduction-cap edge cases", ar: "حالات حدّ الاستقطاع 20٪" },
  insights_cap_current_emi: { en: "Current EMIs over the 20% cap", ar: "أقساط حالية تتجاوز حدّ 20٪" },
  insights_cap_new_emi: { en: "New EMIs over the 20% cap", ar: "أقساط جديدة تتجاوز حدّ 20٪" },
  insights_cap_explain: {
    en: "These cases breach the 20% salary-deduction cap and require automated enforcement before a plan can be issued.",
    ar: "تتجاوز هذه الحالات حدّ استقطاع الراتب البالغ 20٪ وتتطلب إنفاذاً آلياً قبل إصدار أي خطة.",
  },
  insights_proactive_scan: { en: "Proactive risk scan", ar: "المسح الاستباقي للمخاطر" },
  insights_proactive_note: {
    en: "Anonymized patterns derived from the historical dataset — no individual citizen is identifiable.",
    ar: "أنماط مجهولة المصدر مُستخرَجة من البيانات التاريخية — لا يمكن التعرّف على أي مستفيد فرد.",
  },
  col_request_type: { en: "Request type", ar: "نوع الطلب" },
  col_risk: { en: "Risk", ar: "المخاطر" },
  col_cases: { en: "Cases", ar: "الحالات" },
  col_median_score: { en: "Median score", ar: "وسيط الدرجة" },
  col_median_overdue_months: { en: "Median overdue months", ar: "وسيط أشهر التأخر" },
  col_salary_band: { en: "Salary band", ar: "شريحة الراتب" },
  col_exceeds_cap: { en: "Exceeds cap %", ar: "نسبة تجاوز الحد ٪" },
  col_recommended_intervention: { en: "Recommended intervention", ar: "التدخّل الموصى به" },
  insights_what_proves: { en: "What this proves", ar: "ما الذي يثبته هذا" },
  insights_what_proves_body: {
    en: "The organizer dataset shows that arrears rescheduling is a recurring operational workflow, not a rare case. Mizan uses these historical patterns to calibrate proactive risk scoring, validate policy edge cases, and demonstrate earlier intervention before arrears become severe.",
    ar: "تُظهر بيانات المنظِّم أن إعادة جدولة المتأخرات هي سير عمل تشغيلي متكرر، وليست حالة نادرة. يستخدم ميزان هذه الأنماط التاريخية لمعايرة تسجيل المخاطر الاستباقي، والتحقق من حالات السياسة الحدية، وإثبات التدخّل المبكر قبل أن تصبح المتأخرات خطيرة.",
  },
  insights_privacy_note: {
    en: "Aggregated and anonymized from organizer historical data. No raw citizen records are displayed.",
    ar: "مُجمَّعة ومجهولة المصدر من البيانات التاريخية للمنظِّم. لا تُعرض أي سجلات مستفيدين خام.",
  },
  count_label: { en: "count", ar: "العدد" },
};

const OUTCOME: Record<string, { en: string; ar: string }> = {
  UPDATE_INSTALLMENT: { en: "Update installment", ar: "تعديل القسط" },
  TRANSFER_ARREARS: { en: "Transfer arrears to end", ar: "ترحيل المتأخرات للنهاية" },
  MAINTAIN_INSTALLMENT: { en: "Maintain installment", ar: "الإبقاء على القسط" },
  REQUEST_MORE_INFO: { en: "Request more information", ar: "طلب مزيد من المعلومات" },
  REJECT_ACTIVE_REQUEST: { en: "Reject - active request", ar: "رفض - طلب نشط" },
  REFER_TO_OFFICER: { en: "Refer to officer", ar: "إحالة إلى الموظف" },
};

interface I18nCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (k: string) => string;
  outcome: (code?: string | null) => string;
  hc: boolean;
  setHc: (v: boolean) => void;
}

const Ctx = createContext<I18nCtx>(null as any);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(
    () => (localStorage.getItem("mz_lang") as Lang) || "en",
  );
  const [hc, setHc] = useState<boolean>(() => localStorage.getItem("mz_hc") === "1");

  useEffect(() => {
    localStorage.setItem("mz_lang", lang);
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;
  }, [lang]);
  useEffect(() => {
    localStorage.setItem("mz_hc", hc ? "1" : "0");
    document.body.classList.toggle("hc", hc);
  }, [hc]);

  const t = (k: string) => T[k]?.[lang] ?? k;
  const outcome = (code?: string | null) =>
    !code ? "-" : OUTCOME[code]?.[lang] ?? code;

  return (
    <Ctx.Provider value={{ lang, setLang, t, outcome, hc, setHc }}>
      {children}
    </Ctx.Provider>
  );
}

export const useI18n = () => useContext(Ctx);
