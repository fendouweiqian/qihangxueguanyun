export interface EaPlatformVO extends BaseEntity {
  platformId: number;
  platformName: string;
  remark?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaPlatformQuery extends PageQuery {
  platformName?: string;
}

export interface EaPlatformForm {
  platformId?: number;
  platformName: string;
  remark?: string;
}

export interface EaSchoolVO extends BaseEntity {
  schoolId: number;
  platformId: number;
  schoolName: string;
  accessType?: number;
  accessAddress?: string;
  schoolUrl?: string;
  schoolState?: number;
  schoolVideo?: number;
  schoolWork?: number;
  schoolExam?: number;
  schoolFace?: number;
  schoolExam2?: number;
  schoolExamType?: number;
  schoolAnswerOk?: number;
  schoolExamState?: number;
  schoolSumbitTime?: number;
  schoolIpNumber?: number;
  schoolFid?: string;
  schoolCode?: string;
  schoolRemark?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaSchoolQuery extends PageQuery {
  schoolName?: string;
  platformId?: number | string;
}

export interface EaSchoolForm {
  schoolId?: number;
  platformId?: number | string;
  schoolName: string;
  accessType?: number;
  accessAddress?: string;
  schoolUrl?: string;
  schoolState?: number;
  schoolVideo?: number;
  schoolWork?: number;
  schoolExam?: number;
  schoolFace?: number;
  schoolExam2?: number;
  schoolExamType?: number;
  schoolAnswerOk?: number;
  schoolExamState?: number;
  schoolSumbitTime?: number;
  schoolIpNumber?: number;
  schoolFid?: string;
  schoolCode?: string;
  schoolRemark?: string;
}

export interface EaSchoolCacheVO extends BaseEntity {
  cacheId: number;
  sourceSchoolId: number;
  platformId: number;
  platformName: string;
  schoolName: string;
  accessType?: number;
  accessAddress?: string;
  schoolUrl?: string;
  schoolFid?: string;
  schoolCode?: string;
  schoolRemark?: string;
  enabled?: number;
  videoSupported?: number;
  workSupported?: number;
  examSupported?: number;
  examSpecialOrderRequired?: number;
  faceRequired?: number;
  examType?: number;
  answerOk?: number;
  examState?: number;
  submitTime?: number;
  ipNumber?: number;
  createTime?: string;
  updateTime?: string;
}

export interface EaSchoolCacheQuery extends PageQuery {
  sourceSchoolId?: number | string;
  schoolName?: string;
  platformId?: number | string;
  platformName?: string;
  enabled?: number | string;
}

export interface EaSchoolCacheForm {
  cacheId?: number;
  sourceSchoolId?: number | string;
  platformId?: number | string;
  platformName: string;
  schoolName: string;
  accessType?: number;
  accessAddress?: string;
  schoolUrl?: string;
  schoolFid?: string;
  schoolCode?: string;
  schoolRemark?: string;
  enabled?: number;
  videoSupported?: number;
  workSupported?: number;
  examSupported?: number;
  examSpecialOrderRequired?: number;
  faceRequired?: number;
  examType?: number;
  answerOk?: number;
  examState?: number;
  submitTime?: number;
  ipNumber?: number;
}

export interface EaTenantVO extends BaseEntity {
  tenantId: string;
  tenantName: string;
  status?: number;
  balancePoints?: number;
  remark?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaTenantQuery extends PageQuery {
  tenantId?: string;
  tenantName?: string;
  status?: number | string;
}

export interface EaTenantForm {
  tenantId?: string;
  tenantName: string;
  status?: number;
  balancePoints?: number;
  remark?: string;
}

export interface EaStudentVO extends BaseEntity {
  studentId: number;
  tenantId?: string;
  schoolId: number;
  account: string;
  password: string;
  openId?: string;
  name: string;
  studyGrade?: string;
  major?: string;
  phone?: string;
  idCard?: string;
  status?: number;
  loginStatus?: number;
  loginMessage?: string;
  loginCheckedAt?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaStudentQuery extends PageQuery {
  schoolId?: number | string;
  account?: string;
  name?: string;
  phone?: string;
  status?: number | string;
}

export interface EaStudentForm {
  studentId?: number;
  schoolId?: number | string;
  account: string;
  password: string;
  openId?: string;
  name: string;
  studyGrade?: string;
  major?: string;
  phone?: string;
  idCard?: string;
  status?: number;
  loginStatus?: number;
  loginMessage?: string;
  loginCheckedAt?: string;
}

export interface EaStudentFetchNameRequest {
  schoolId?: number | string;
  account: string;
  password: string;
  openId?: string;
}

export interface EaStudentFetchNameVO {
  name: string;
  validated?: boolean;
}

export interface EaStudentLoginCheckRequest {
  studentId: number | string;
  orderId?: number | string;
}

export interface EaStudentLoginCheckVO {
  ok?: boolean;
  loginStatus?: number;
  loginMessage?: string;
  loginCheckedAt?: string;
  adapter?: string;
  studentName?: string;
  studyGrade?: string;
  major?: string;
}

export interface EaOrderVO extends BaseEntity {
  orderId: number | string;
  tenantId?: string;
  studentId: number;
  schoolId: number;
  platformId: number;
  orderType: number;
  courseName?: string;
  courseCode?: string;
  term?: string;
  examStartAt?: string;
  examEndAt?: string;
  status?: number;
  costPoints: number;
  paidAt?: string;
  remark?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaOrderDetailVO {
  order?: EaOrderVO;
  student?: EaStudentVO;
  school?: EaSchoolVO;
  platform?: EaPlatformVO;
  courseProgress?: EaCourseProgressVO;
  examProgress?: EaExamProgressVO;
  courseProgressItems?: EaCourseProgressItemVO[];
  examProgressItems?: EaExamProgressItemVO[];
  tasks?: EaTaskVO[];
  logs?: EaTaskLogVO[];
}

export interface EaOrderQuery extends PageQuery {
  orderId?: number | string;
  studentId?: number | string;
  schoolId?: number | string;
  platformId?: number | string;
  status?: number | string;
}

export interface EaOrderForm {
  orderId?: number | string;
  studentId?: number | string;
  schoolId?: number | string;
  platformId?: number | string;
  orderType?: number;
  courseName?: string;
  courseCode?: string;
  term?: string;
  examStartAt?: string;
  examEndAt?: string;
  status?: number;
  costPoints?: number;
  paidAt?: string;
  remark?: string;
}

export interface EaTaskVO extends BaseEntity {
  taskId: number | string;
  orderId: number | string;
  tenantId?: string;
  taskType?: number;
  status?: number;
  triggerAt?: string;
  workerCode?: string;
  startedAt?: string;
  finishedAt?: string;
  heartbeatAt?: string;
  retryCount?: number;
  lastError?: string;
  resultSummary?: string;
  taskConfigJson?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaTaskQuery extends PageQuery {
  orderId?: number | string;
  status?: number | string;
  taskType?: number | string;
}

export interface EaTaskForm {
  taskId?: number | string;
  orderId?: number | string;
  taskType?: number;
  status?: number;
  triggerAt?: string;
  workerCode?: string;
  startedAt?: string;
  finishedAt?: string;
  heartbeatAt?: string;
  retryCount?: number;
  lastError?: string;
  resultSummary?: string;
  taskConfigJson?: string;
}

export interface EaTaskLogVO extends BaseEntity {
  logId: number | string;
  taskId: number | string;
  orderId?: number | string;
  tenantId?: string;
  workerCode?: string;
  seqNo?: number;
  level?: string;
  bizType?: string;
  bizTitle?: string;
  bizStatus?: number;
  message?: string;
  failureReason?: string;
  createdAt?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaTaskLogQuery extends PageQuery {
  taskId?: number | string;
  orderId?: number | string;
  tenantId?: string;
  workerCode?: string;
  level?: string;
}

export interface EaRunnerNodeVO extends BaseEntity {
  nodeId: number;
  workerCode: string;
  version?: string;
  hostName?: string;
  status?: number;
  currentTaskId?: number;
  currentOrderId?: number;
  lastError?: string;
  heartbeatAt?: string;
  startedAt?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaRunnerNodeQuery extends PageQuery {
  workerCode?: string;
  status?: number | string;
  hostName?: string;
}

export interface EaRunnerNodeForm {
  nodeId?: number;
  workerCode: string;
  version?: string;
  hostName?: string;
  status?: number;
  currentTaskId?: number | string;
  currentOrderId?: number | string;
  lastError?: string;
  heartbeatAt?: string;
  startedAt?: string;
}

export interface EaRunnerSettingVO extends BaseEntity {
  settingId: number;
  tenantId: string;
  aiType?: string;
  aiUrl?: string;
  aiModel?: string;
  aiApiKey?: string;
  externalQuestionUrl?: string;
  completionTone?: number;
  colorLog?: number;
  logLevel?: string;
  logModel?: number;
  pollIntervalSeconds?: number;
  maxParallelTasks?: number;
  taskTimeoutSeconds?: number;
  logRetentionDays?: number;
  remark?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaRunnerSettingQuery extends PageQuery {
  tenantId?: string;
  aiType?: string;
}

export interface EaRunnerSettingForm {
  settingId?: number;
  tenantId: string;
  aiType?: string;
  aiUrl?: string;
  aiModel?: string;
  aiApiKey?: string;
  externalQuestionUrl?: string;
  completionTone?: number;
  colorLog?: number;
  logLevel?: string;
  logModel?: number;
  pollIntervalSeconds?: number;
  maxParallelTasks?: number;
  taskTimeoutSeconds?: number;
  logRetentionDays?: number;
  remark?: string;
}

export interface EaTikuFailureVO extends BaseEntity {
  failureId: number | string;
  taskId?: number | string;
  orderId?: number | string;
  tenantId?: string;
  provider?: string;
  question?: string;
  optionsJson?: string;
  reason?: string;
  rawResponse?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaTikuFailureQuery extends PageQuery {
  taskId?: number | string;
  orderId?: number | string;
  tenantId?: string;
  provider?: string;
}

export interface EaTaskDetailVO {
  task?: EaTaskVO;
  courseProgress?: EaCourseProgressVO;
  examProgress?: EaExamProgressVO;
  courseProgressItems?: EaCourseProgressItemVO[];
  examProgressItems?: EaExamProgressItemVO[];
  logs?: EaTaskLogVO[];
  tikuFailures?: EaTikuFailureVO[];
}

export interface EaCourseProgressVO extends BaseEntity {
  progressId: number | string;
  orderId: number | string;
  studentId?: number | string;
  studentName?: string;
  studentAccount?: string;
  studyGrade?: string;
  major?: string;
  loginStatus?: number;
  loginMessage?: string;
  loginCheckedAt?: string;
  tenantId?: string;
  courseName?: string;
  term?: string;
  videoStatus?: number;
  videoNote?: string;
  videoTime?: string;
  workStatus?: number;
  workNote?: string;
  workTime?: string;
  examStatus?: number;
  examNote?: string;
  examTime?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaCourseProgressQuery extends PageQuery {
  orderId?: number | string;
  courseName?: string;
  term?: string;
  studentAccount?: string;
}

export interface EaCourseProgressForm {
  progressId?: number | string;
  orderId?: number | string;
  courseName?: string;
  term?: string;
  videoStatus?: number;
  videoNote?: string;
  videoTime?: string;
  workStatus?: number;
  workNote?: string;
  workTime?: string;
  examStatus?: number;
  examNote?: string;
  examTime?: string;
}

export interface EaCourseProgressItemVO extends BaseEntity {
  itemId: number | string;
  orderId: number | string;
  tenantId?: string;
  courseName?: string;
  courseType?: string;
  requiredFlag?: number;
  term?: string;
  learningStatus?: number;
  learningPercent?: number | string;
  learningText?: string;
  workStatus?: number;
  latestTime?: string;
}

export interface EaExamProgressVO extends BaseEntity {
  examProgressId: number | string;
  orderId: number | string;
  tenantId?: string;
  status?: number;
  score?: number;
  note?: string;
  finishedAt?: string;
  createTime?: string;
  updateTime?: string;
}

export interface EaExamProgressQuery extends PageQuery {
  orderId?: number | string;
  status?: number | string;
}

export interface EaExamProgressForm {
  examProgressId?: number | string;
  orderId?: number | string;
  status?: number;
  score?: number;
  note?: string;
  finishedAt?: string;
}

export interface EaExamProgressItemVO extends BaseEntity {
  itemId: number | string;
  orderId: number | string;
  tenantId?: string;
  examName?: string;
  examStatus?: number;
  score?: number | string;
  examTime?: string;
  latestTime?: string;
  remark?: string;
  frozenFlag?: number;
  frozenReason?: string;
  frozenTime?: string;
}

export interface EaFaceMediaVO extends BaseEntity {
  faceMediaId: number;
  tenantId?: string;
  studentId: number;
  fileUrl?: string;
  fileType?: string;
  status?: number;
  uploadedBy?: number;
  createTime?: string;
  updateTime?: string;
}

export interface EaFaceMediaQuery extends PageQuery {
  studentId?: number | string;
  status?: number | string;
}

export interface EaFaceMediaForm {
  faceMediaId?: number;
  studentId?: number | string;
  fileUrl?: string;
  fileType?: string;
  status?: number;
  uploadedBy?: number;
}

export interface EaLedgerVO extends BaseEntity {
  ledgerId: number | string;
  tenantId?: string;
  orderId?: number | string;
  changePoints?: number;
  giftPoints?: number;
  type?: number;
  operatorUserId?: number;
  remark?: string;
  createTime?: string;
}

export interface EaLedgerQuery extends PageQuery {
  tenantId?: string;
  orderId?: number | string;
  type?: number | string;
}

export interface EaRechargeVO extends BaseEntity {
  rechargeId: number;
  tenantId?: string;
  operatorUserId?: number;
  rechargePoints: number;
  giftPoints?: number;
  remark?: string;
  createTime?: string;
}

export interface EaRechargeQuery extends PageQuery {
  tenantId?: string;
}

export interface EaRechargeForm {
  rechargeId?: number;
  tenantId?: string;
  rechargePoints?: number;
  giftPoints?: number;
  remark?: string;
}
