<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="课程名称" prop="courseName">
              <el-input v-model="queryParams.courseName" placeholder="请输入课程名称" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="学员账号" prop="studentAccount">
              <el-input v-model="queryParams.studentAccount" placeholder="请输入学员账号" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="学期" prop="term">
              <el-input v-model="queryParams.term" placeholder="请输入学期" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
              <el-button icon="Refresh" @click="resetQuery">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </transition>

    <el-card shadow="hover">
      <template #header>
        <div class="toolbar-row">
          <div>
            <div class="toolbar-title">课程订单</div>
            <div class="toolbar-tip">提交课程订单后，在列表中查看学习、考试进度。</div>
          </div>
          <div class="toolbar-actions">
            <el-button type="primary" icon="Plus" @click="openSubmitDialog">提交订单</el-button>
            <right-toolbar v-model:show-search="showSearch" @query-table="getList" />
          </div>
        </div>
      </template>

      <el-table v-loading="loading" border :data="progressList">
        <el-table-column label="姓名" align="center" width="130" :show-overflow-tooltip="true">
          <template #default="scope">
            <el-button
              v-if="shouldShowRetry(scope.row)"
              link
              type="primary"
              size="small"
              :loading="retryingStudentId === String(scope.row.studentId || '')"
              @click="retryStudentProfile(scope.row)"
            >
              重试获取
            </el-button>
            <span v-else>{{ progressStudentName(scope.row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="账号" align="center" min-width="170" :show-overflow-tooltip="true">
          <template #default="scope">
            <span>{{ scope.row.studentAccount || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="课程信息" align="left" min-width="260" :show-overflow-tooltip="true">
          <template #default="scope">
            <div class="course-info">{{ compactCourseInfo(scope.row) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="进度" align="center" min-width="260">
          <template #default="scope">
            <div class="progress-tags">
              <el-tag :type="progressStatusTag(scope.row.videoStatus)">学习：{{ progressStatusLabel(scope.row.videoStatus) }}</el-tag>
              <el-tag :type="progressStatusTag(scope.row.examStatus)">考试：{{ progressCardStatusLabel('exam', scope.row.examStatus) }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="最新更新时间" align="center" min-width="180">
          <template #default="scope">
            <span>{{ latestProgressTime(scope.row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="120">
          <template #default="scope">
            <el-tooltip content="查看进度" placement="top">
              <el-button link type="primary" icon="View" @click="handleDetail(scope.row)">查看进度</el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>

    <el-dialog v-model="submitVisible" title="提交订单" width="620px" append-to-body class="submit-order-dialog">
      <el-form ref="submitFormRef" :model="submitForm" :rules="submitRules" label-position="top" class="quick-submit-form">
        <div class="autofill-decoys" aria-hidden="true">
          <input type="text" name="username" tabindex="-1" autocomplete="username" />
          <input type="text" name="password" tabindex="-1" autocomplete="off" />
        </div>
        <el-form-item label="学校" prop="schoolId">
          <el-select v-model="submitForm.schoolId" placeholder="请选择学校" filterable @change="handleSchoolChange">
            <el-option v-for="item in schoolOptions" :key="item.cacheId" :label="item.displayLabel" :value="item.cacheId" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号" prop="account">
          <el-input v-model="submitForm.account" placeholder="请输入账号" clearable autocomplete="off" @keyup.enter="submitOrder" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="submitForm.password" placeholder="请输入密码" name="student_login_pass" autocomplete="off" @keyup.enter="submitOrder" />
        </el-form-item>
      </el-form>

      <div v-if="selectedSchool" class="school-strip">
        <div class="school-name">{{ selectedSchool.schoolName }}</div>
        <div class="school-support-grid">
          <span>网课</span>
          <el-tag size="small" :type="supportTag(selectedSchool.videoSupported)">{{ supportLabel(selectedSchool.videoSupported) }}</el-tag>
          <span>作业</span>
          <el-tag size="small" :type="supportTag(selectedSchool.workSupported)">{{ supportLabel(selectedSchool.workSupported) }}</el-tag>
          <span>考试</span>
          <el-tag size="small" :type="supportTag(selectedSchool.examSupported)">{{ supportLabel(selectedSchool.examSupported) }}</el-tag>
          <span>人脸识别</span>
          <el-tag size="small" :type="requireTag(selectedSchool.faceRequired)">{{ requireLabel(selectedSchool.faceRequired) }}</el-tag>
        </div>
      </div>

      <template #footer>
        <el-button @click="submitVisible = false">取消</el-button>
        <el-button icon="Refresh" @click="resetSubmitForm">重置</el-button>
        <el-button type="primary" icon="Check" :loading="submitting" @click="submitOrder">提交并查询</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="课程进度详情" width="1080px" append-to-body class="progress-detail-dialog">
      <div v-loading="detailLoading">
        <el-empty v-if="!detail.courseProgress && !detail.order" description="暂无执行详情" />
        <template v-else>
          <div class="detail-action-bar">
            <div class="detail-action-tip">当前已返回 {{ courseDetailRows.length }} 门课程；如平台数据有变化，可重新登录拉取完整课程与考试列表。</div>
            <div class="detail-action-buttons">
              <el-button icon="Refresh" :loading="refreshingDetail" @click="refreshDetailSnapshot">重新获取课程/考试信息</el-button>
              <el-button type="primary" icon="VideoPlay" :loading="restartingExam" @click="restartExamTask">重新开始考试</el-button>
            </div>
          </div>
          <el-descriptions :column="2" border class="mb-4 order-summary">
            <el-descriptions-item label="订单ID">{{ detail.order?.orderId || '-' }}</el-descriptions-item>
            <el-descriptions-item label="学员姓名">{{ progressStudentDisplayName }}</el-descriptions-item>
            <el-descriptions-item label="学员账号">{{ progressStudentAccount }}</el-descriptions-item>
            <el-descriptions-item label="课程">{{ detailCourseLabel }}</el-descriptions-item>
            <el-descriptions-item label="学期">{{ termLabel(detail.courseProgress?.term || detail.order?.term) }}</el-descriptions-item>
            <el-descriptions-item label="学籍年级">{{ progressStudyGrade }}</el-descriptions-item>
            <el-descriptions-item label="培养专业">{{ progressMajor }}</el-descriptions-item>
            <el-descriptions-item label="平台">{{ detail.platform?.platformName || '-' }}</el-descriptions-item>
          </el-descriptions>
          <el-alert v-if="latestTask" class="task-status-alert" :closable="false" show-icon>
            <template #title>
              <span>最近任务：</span>
              <el-tag :type="taskStatusTag(latestTask.status)" size="small">{{ taskStatusLabel(latestTask.status) }}</el-tag>
              <span class="task-status-meta">更新时间：{{ taskTimeLabel(latestTask) }}</span>
              <span v-if="latestTask.workerCode" class="task-status-meta">执行节点：{{ latestTask.workerCode }}</span>
            </template>
            <template v-if="latestTask.lastError" #default>
              <div class="task-last-error">{{ latestTask.lastError }}</div>
            </template>
          </el-alert>

          <el-tabs v-model="detailTab" class="user-detail-tabs">
            <el-tab-pane :label="`我的课程（${courseDetailRows.length}）`" name="course">
              <el-table border :data="courseDetailRows" class="detail-table user-detail-table">
                <el-table-column label="课程" min-width="260" show-overflow-tooltip>
                  <template #default="scope">
                    <div class="course-cell">
                      <span class="course-cell__name">{{ scope.row.courseName || '-' }}</span>
                      <el-tag v-if="scope.row.requiredFlag === 1 || scope.row.courseType" size="small" type="primary" effect="light">
                        {{ scope.row.courseType || '必修课' }}
                      </el-tag>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="学习进度" min-width="260">
                  <template #default="scope">
                    <div class="learning-progress">
                      <el-progress :percentage="scope.row.learningPercentValue" :status="progressBarStatus(scope.row.learningStatus)" />
                      <span class="learning-progress__text">{{ learningProgressText(scope.row) }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="最新更新时间" prop="latestTime" width="180" />
              </el-table>
            </el-tab-pane>
            <el-tab-pane :label="`我的考试（${examDetailRows.length}）`" name="exam">
              <el-table border :data="examDetailRows" class="detail-table user-detail-table">
                <el-table-column label="考试名称" prop="examName" min-width="260" show-overflow-tooltip />
                <el-table-column label="考试状态" align="center" width="120">
                  <template #default="scope">
                    <el-tag type="warning" effect="light">{{ examOriginalStatus(scope.row) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="提交状态" align="center" width="120">
                  <template #default="scope">
                    <el-tag type="success" effect="light">{{ examSubmitStatus(scope.row) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="冻结" align="center" width="110">
                  <template #default="scope">
                    <el-tag v-if="isExamFrozen(scope.row)" type="info" effect="plain">已冻结</el-tag>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="成绩" align="center" width="100">
                  <template #default="scope">{{ scope.row.score ?? '-' }}</template>
                </el-table-column>
                <el-table-column label="时间" prop="examTime" width="180" />
                <el-table-column label="操作" align="center" width="130" fixed="right">
                  <template #default="scope">
                    <el-button
                      v-if="canToggleExamFrozen(scope.row)"
                      link
                      :type="isExamFrozen(scope.row) ? 'success' : 'warning'"
                      :loading="freezingExamItemId === String(scope.row.itemId)"
                      @click="toggleExamFrozen(scope.row)"
                    >
                      {{ isExamFrozen(scope.row) ? '解冻' : '冻结本场' }}
                    </el-button>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>

          <el-collapse class="debug-collapse">
            <el-collapse-item title="执行流程（开发调试）" name="debug">
              <el-tabs v-model="debugTab" class="debug-tabs">
                <el-tab-pane label="学习" name="video">
                  <el-table border :data="videoTimeline" class="detail-table">
                    <el-table-column label="时间" align="center" prop="time" width="180" />
                    <el-table-column label="状态" align="center" width="110">
                      <template #default="scope">
                        <el-tag :type="timelineStatusTag(scope.row.status)">{{ timelineStatusLabel(scope.row.status) }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="内容" prop="content" min-width="620" show-overflow-tooltip />
                  </el-table>
                </el-tab-pane>
                <el-tab-pane label="作业" name="work">
                  <el-table border :data="workTimeline" class="detail-table">
                    <el-table-column label="时间" align="center" prop="time" width="180" />
                    <el-table-column label="状态" align="center" width="110">
                      <template #default="scope">
                        <el-tag :type="timelineStatusTag(scope.row.status)">{{ timelineStatusLabel(scope.row.status) }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="内容" prop="content" min-width="620" show-overflow-tooltip />
                  </el-table>
                </el-tab-pane>
                <el-tab-pane label="考试" name="exam">
                  <el-table border :data="examTimeline" class="detail-table">
                    <el-table-column label="时间" align="center" prop="time" width="180" />
                    <el-table-column label="状态" align="center" width="110">
                      <template #default="scope">
                        <el-tag :type="timelineStatusTag(scope.row.status)">{{ timelineStatusLabel(scope.row.status) }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="内容" prop="content" min-width="620" show-overflow-tooltip />
                  </el-table>
                </el-tab-pane>
              </el-tabs>
            </el-collapse-item>
          </el-collapse>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<script setup name="EduCourseProgress" lang="ts">
import { listCourseProgress } from '@/api/education/courseProgress';
import { addOrder, getOrderDetail, listOrder } from '@/api/education/order';
import { freezeExamProgressItem, unfreezeExamProgressItem } from '@/api/education/examProgressItem';
import { listSchool } from '@/api/education/school';
import { addStudent, checkStudentLogin, listStudent, updateStudent } from '@/api/education/student';
import { runOrderTask } from '@/api/education/task';
import {
  EaCourseProgressItemVO,
  EaCourseProgressQuery,
  EaCourseProgressVO,
  EaExamProgressItemVO,
  EaOrderForm,
  EaOrderDetailVO,
  EaOrderVO,
  EaSchoolVO,
  EaStudentForm,
  EaStudentVO,
  EaTaskVO,
  EaTaskLogVO
} from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;
const route = useRoute();
const router = useRouter();

type TimelineRow = {
  id: string;
  time: string;
  status: number;
  content: string;
};

type LogBizType = 'VIDEO' | 'WORK' | 'EXAM' | 'SYSTEM';

type CourseDetailRow = EaCourseProgressItemVO & {
  learningPercentValue: number;
};

type SchoolOption = EaSchoolVO & {
  cacheId: number;
  sourceSchoolId: number;
  displayLabel: string;
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
};

const progressList = ref<EaCourseProgressVO[]>([]);
const loading = ref(true);
const detailLoading = ref(false);
const detailVisible = ref(false);
const submitVisible = ref(false);
const submitting = ref(false);
const retryingStudentId = ref('');
const freezingExamItemId = ref('');
const refreshingDetail = ref(false);
const restartingExam = ref(false);
const showSearch = ref(true);
const total = ref(0);
const detail = ref<EaOrderDetailVO>({});
const detailTab = ref('course');
const debugTab = ref('video');

const queryFormRef = ref<ElFormInstance>();
const submitFormRef = ref<ElFormInstance>();
const schoolOptions = ref<SchoolOption[]>([]);
const selectedSchool = ref<SchoolOption>();
const submitForm = reactive({
  schoolId: undefined as number | undefined,
  account: '',
  password: ''
});

const data = reactive<PageData<Record<string, never>, EaCourseProgressQuery>>({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    orderId: undefined,
    courseName: '',
    studentAccount: '',
    term: ''
  },
  rules: {}
});

const { queryParams } = toRefs(data);

const progressStatusLabel = (status?: number) => {
  if (status === 1) {
    return '已完成';
  }
  if (status === 2) {
    return '失败';
  }
  if (status === 3) {
    return '处理中';
  }
  return '未开始';
};

const progressStatusTag = (status?: number) => {
  if (status === 1) {
    return 'success';
  }
  if (status === 2) {
    return 'danger';
  }
  if (status === 3) {
    return 'warning';
  }
  return 'info';
};

const cleanStudentName = (name?: string, account?: string) => {
  const text = String(name || '').trim();
  const accountText = String(account || '').trim();
  if (!text || text === accountText || !/[\u4e00-\u9fff]/.test(text)) {
    return '';
  }
  return text;
};

const submitRules = {
  schoolId: [{ required: true, message: '请选择学校', trigger: 'change' }],
  account: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
};

const supportOptions = [
  { label: '未知', value: 0, tagType: 'info' },
  { label: '支持', value: 1, tagType: 'success' },
  { label: '不支持', value: 2, tagType: 'danger' }
];

const requireOptions = [
  { label: '未知', value: 0, tagType: 'info' },
  { label: '需要', value: 1, tagType: 'warning' },
  { label: '不需要', value: 2, tagType: 'success' }
];

const supportLabel = (value?: number) => supportOptions.find((item) => item.value === value)?.label ?? '未知';
const supportTag = (value?: number): ElTagType => (supportOptions.find((item) => item.value === value)?.tagType as ElTagType) ?? 'info';
const requireLabel = (value?: number) => requireOptions.find((item) => item.value === value)?.label ?? '未知';
const requireTag = (value?: number): ElTagType => (requireOptions.find((item) => item.value === value)?.tagType as ElTagType) ?? 'info';

const progressStudentName = (row: EaCourseProgressVO) => cleanStudentName(row.studentName, row.studentAccount) || '未返回';

const shouldShowRetry = (row: EaCourseProgressVO) => !!row.studentId && progressStudentName(row) === '未返回';

const progressStudentAccount = computed(() => {
  return detail.value.courseProgress?.studentAccount || detail.value.student?.account || '-';
});

const progressStudentDisplayName = computed(() => {
  const account = detail.value.courseProgress?.studentAccount || detail.value.student?.account;
  const name = detail.value.courseProgress?.studentName || detail.value.student?.name;
  return cleanStudentName(name, account) || '未返回';
});

const termLabel = (term?: string) => String(term || '').trim() || '未返回';
const profileLabel = (value?: string) => String(value || '').trim() || '未返回';

const compactCourseInfo = (row: EaCourseProgressVO) => {
  const parts = [row.courseName, row.term, row.studyGrade, row.major].map((item) => String(item || '').trim()).filter(Boolean);
  return parts.length ? parts.join(' / ') : '未返回';
};

const progressStudyGrade = computed(() => profileLabel(detail.value.courseProgress?.studyGrade || detail.value.student?.studyGrade));
const progressMajor = computed(() => profileLabel(detail.value.courseProgress?.major || detail.value.student?.major));

const latestTask = computed(() => {
  const tasks = detail.value.tasks || [];
  if (!tasks.length) {
    return undefined;
  }
  return [...tasks].sort((left, right) => String(right.taskId).localeCompare(String(left.taskId)))[0];
});

const taskStatusLabel = (status?: number) => {
  if (status === 0) {
    return '待执行';
  }
  if (status === 1) {
    return '执行中';
  }
  if (status === 2) {
    return '已完成';
  }
  if (status === 3) {
    return '执行失败';
  }
  return '未知';
};

const taskStatusTag = (status?: number) => {
  if (status === 0) {
    return 'info';
  }
  if (status === 1) {
    return 'warning';
  }
  if (status === 2) {
    return 'success';
  }
  if (status === 3) {
    return 'danger';
  }
  return 'info';
};

const taskTimeLabel = (task?: EaTaskVO) => task?.finishedAt || task?.heartbeatAt || task?.startedAt || task?.triggerAt || '-';

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

const pollLatestTaskAfterRestart = async () => {
  for (let index = 0; index < 6; index += 1) {
    await wait(index === 0 ? 800 : 2000);
    await loadOrderDetail();
    const task = latestTask.value;
    if (!task || task.status === 2 || task.status === 3 || task.status === 1) {
      return task;
    }
  }
  return latestTask.value;
};

const detailCourseLabel = computed(() => {
  const courseName = String(detail.value.courseProgress?.courseName || detail.value.order?.courseName || '').trim();
  const schoolName = String(detail.value.school?.schoolName || '').trim();
  if (courseName && schoolName && courseName !== schoolName) {
    return `${courseName} / ${schoolName}`;
  }
  return courseName || schoolName || '-';
});

const progressCardStatusLabel = (key: string, status?: number) => {
  if (key === 'exam' && (status || 0) === 0) {
    return '考试未开始';
  }
  return progressStatusLabel(status);
};

const normalizePercent = (value?: number | string) => {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Number(numberValue.toFixed(1))));
};

const inferPercentFromStatus = (status?: number) => (status === 1 ? 100 : 0);

const progressBarStatus = (status?: number) => {
  if (status === 1) {
    return 'success';
  }
  if (status === 2) {
    return 'exception';
  }
  return undefined;
};

const learningProgressText = (row: CourseDetailRow) => {
  if (row.learningStatus === 1 || row.learningPercentValue >= 100) {
    return '100%';
  }
  const text = String(row.learningText || '').trim();
  if (text && !text.includes('[学习通]')) {
    return text;
  }
  return progressStatusLabel(row.learningStatus);
};

const remarkField = (remark: string | undefined, label: string) => {
  const text = String(remark || '');
  const match = text.match(new RegExp(`${label}[：:]\\s*([^/]+)`));
  return match ? match[1].trim() : '';
};

const examOriginalStatus = (row: EaExamProgressItemVO) => {
  return remarkField(row.remark, '考试状态') || progressCardStatusLabel('exam', row.examStatus);
};

const examSubmitStatus = (row: EaExamProgressItemVO) => {
  return remarkField(row.remark, '提交状态') || (row.examStatus === 1 ? '已提交' : progressCardStatusLabel('exam', row.examStatus));
};

const isExamFrozen = (row: EaExamProgressItemVO) => String(row.frozenFlag ?? 0) === '1';

const canToggleExamFrozen = (row: EaExamProgressItemVO) => {
  if (!row?.itemId) {
    return false;
  }
  if (isExamFrozen(row)) {
    return true;
  }
  return row.examStatus !== 1 && examSubmitStatus(row) !== '已提交';
};

const courseDetailRows = computed<CourseDetailRow[]>(() => {
  const rows = detail.value.courseProgressItems || [];
  if (rows.length) {
    return rows.map((row) => ({
      ...row,
      latestTime: row.latestTime || row.updateTime || '-',
      learningPercentValue: normalizePercent(row.learningPercent ?? inferPercentFromStatus(row.learningStatus))
    }));
  }
  const progress = detail.value.courseProgress;
  if (!progress) {
    return [];
  }
  return [
    {
      itemId: 'fallback-course',
      orderId: progress.orderId,
      tenantId: progress.tenantId,
      courseName: progress.courseName || detail.value.order?.courseName || '课程学习',
      courseType: '',
      requiredFlag: 0,
      term: progress.term || detail.value.order?.term,
      learningStatus: progress.videoStatus,
      learningPercent: inferPercentFromStatus(progress.videoStatus),
      learningPercentValue: inferPercentFromStatus(progress.videoStatus),
      learningText: progressStatusLabel(progress.videoStatus),
      workStatus: progress.workStatus,
      latestTime: progress.videoTime || progress.workTime || progress.updateTime || '-'
    }
  ];
});

const examDetailRows = computed<EaExamProgressItemVO[]>(() => {
  const rows = detail.value.examProgressItems || [];
  if (rows.length) {
    return rows.map((row) => ({
      ...row,
      examTime: row.examTime || row.latestTime || row.updateTime || '-',
      latestTime: row.latestTime || row.updateTime || '-'
    }));
  }
  const progress = detail.value.courseProgress;
  const exam = detail.value.examProgress;
  if (!progress && !exam) {
    return [];
  }
  const status = progress?.examStatus ?? exam?.status;
  return [
    {
      itemId: 'fallback-exam',
      orderId: progress?.orderId || exam?.orderId || detail.value.order?.orderId || '',
      tenantId: progress?.tenantId || exam?.tenantId,
      examName: progress?.courseName || detail.value.order?.courseName || '我的考试',
      examStatus: status,
      score: exam?.score,
      examTime: progress?.examTime || exam?.finishedAt || '-',
      latestTime: progress?.examTime || exam?.finishedAt || progress?.updateTime || '-',
      remark: ''
    }
  ];
});

const timelineStatusTag = (status?: number) => {
  if (status === 1) {
    return 'success';
  }
  if (status === 2) {
    return 'danger';
  }
  if (status === 3) {
    return 'warning';
  }
  return 'info';
};

const timelineStatusLabel = (status?: number) => {
  if (status === 1) {
    return '已完成';
  }
  if (status === 2) {
    return '失败';
  }
  if (status === 3) {
    return '处理中';
  }
  return '记录';
};

const stripAnsi = (value?: string) => (value || '').replace(/\x1B\[[0-9;]*m/g, '');

const resolveBizType = (log: EaTaskLogVO, message: string): LogBizType => {
  if (log.bizType === 'VIDEO' || log.bizType === 'WORK' || log.bizType === 'EXAM') {
    return log.bizType;
  }
  if (message.includes('作业')) {
    return 'WORK';
  }
  if (message.includes('考试')) {
    return 'EXAM';
  }
  if (message.includes('学习') || message.includes('章节')) {
    return 'VIDEO';
  }
  return 'SYSTEM';
};

const timelineRows = computed(() => {
  const logs = detail.value.logs || [];
  return logs
    .filter((log) => (log.bizStatus || 0) > 0)
    .map((log: EaTaskLogVO, index: number) => {
      const content = stripAnsi(log.message);
      const status = log.bizStatus === 0 || log.bizStatus === undefined ? (log.level === 'ERROR' ? 2 : 0) : log.bizStatus;
      return {
        id: `${log.logId || index}`,
        time: log.createdAt || log.createTime || '-',
        bizType: resolveBizType(log, content),
        status,
        content: log.failureReason || content
      };
    });
});

const timelineByType = (bizType: LogBizType) => {
  return timelineRows.value.filter((row) => row.bizType === bizType);
};

const videoTimeline = computed<TimelineRow[]>(() => timelineByType('VIDEO'));
const workTimeline = computed<TimelineRow[]>(() => timelineByType('WORK'));
const examTimeline = computed<TimelineRow[]>(() => timelineByType('EXAM'));

const latestProgressTime = (row: EaCourseProgressVO) => row.videoTime || row.workTime || row.examTime || row.updateTime || row.createTime || '-';

const retryStudentProfile = async (row: EaCourseProgressVO) => {
  const studentId = String(row.studentId || '');
  if (!studentId) {
    proxy?.$modal.msgWarning('未找到学员ID，无法重试');
    return;
  }
  retryingStudentId.value = studentId;
  try {
    proxy?.$modal.msg('正在重新登录并获取基础信息与课程信息...');
    const { data } = await checkStudentLogin({ studentId, orderId: row.orderId });
    const name = cleanStudentName(data?.studentName, row.studentAccount);
    proxy?.$modal.msgSuccess(name || data?.studyGrade || data?.major ? '登录成功，信息已更新' : '登录成功，暂未返回基础信息');
    await getList();
  } catch (error: any) {
    await getList();
    proxy?.$modal.msgError(error?.message || '重新获取基础信息失败');
    console.error(error);
  } finally {
    retryingStudentId.value = '';
  }
};

const loadOrderDetail = async (row?: EaCourseProgressVO) => {
  const orderId = row?.orderId || detail.value.order?.orderId || detail.value.courseProgress?.orderId;
  if (!orderId) {
    return;
  }
  const { data } = await getOrderDetail(orderId);
  detail.value = data || { courseProgress: row };
  if (!detail.value.courseProgress && row) {
    detail.value.courseProgress = row;
  }
};

const refreshDetailSnapshot = async () => {
  const studentId = detail.value.student?.studentId || detail.value.courseProgress?.studentId;
  const orderId = detail.value.order?.orderId || detail.value.courseProgress?.orderId;
  if (!studentId || !orderId) {
    proxy?.$modal.msgWarning('缺少学员或订单信息，无法重新获取');
    return;
  }
  refreshingDetail.value = true;
  try {
    proxy?.$modal.msg('正在重新登录并获取课程、考试信息...');
    await checkStudentLogin({ studentId, orderId });
    await loadOrderDetail();
    await getList();
    proxy?.$modal.msgSuccess('课程与考试信息已重新获取');
  } catch (error: any) {
    await getList();
    proxy?.$modal.msgError(error?.message || '重新获取课程与考试信息失败');
    console.error(error);
  } finally {
    refreshingDetail.value = false;
  }
};

const toggleExamFrozen = async (row: EaExamProgressItemVO) => {
  if (!row?.orderId || !row.examName) {
    proxy?.$modal.msgWarning('缺少订单或考试名称，无法操作');
    return;
  }
  const orderId = row.orderId;
  const examName = row.examName;
  const rowKey = row.itemId ? String(row.itemId) : `${orderId}:${examName}`;
  const frozen = isExamFrozen(row);
  const actionText = frozen ? '解冻' : '冻结';
  await proxy?.$modal.confirm(`是否${actionText}考试「${examName}」？`);
  freezingExamItemId.value = rowKey;
  try {
    if (frozen) {
      await unfreezeExamProgressItem(orderId, examName);
    } else {
      await freezeExamProgressItem(orderId, examName, '手动冻结，先执行其它考试');
    }
    await loadOrderDetail();
    await getList();
    proxy?.$modal.msgSuccess(`${actionText}成功`);
  } catch (error: any) {
    proxy?.$modal.msgError(error?.message || error || `${actionText}失败`);
    console.error(error);
  } finally {
    freezingExamItemId.value = '';
  }
};

const restartExamTask = async () => {
  const orderId = detail.value.order?.orderId || detail.value.courseProgress?.orderId;
  if (!orderId) {
    proxy?.$modal.msgWarning('缺少订单信息，无法重新开始考试');
    return;
  }
  await proxy?.$modal.confirm('是否将该订单重新入队？执行节点领取后会继续执行考试任务。');
  restartingExam.value = true;
  try {
    await runOrderTask(orderId);
    const task = await pollLatestTaskAfterRestart();
    await getList();
    if (task?.status === 1) {
      proxy?.$modal.msgSuccess(`任务已被执行节点领取，当前状态：${taskStatusLabel(task.status)}`);
      return;
    }
    if (task?.status === 3) {
      proxy?.$modal.msgError(task.lastError || '任务已执行但失败，请查看开发调试信息');
      return;
    }
    proxy?.$modal.msgSuccess('任务已重新入队，等待执行节点领取');
  } catch (error: any) {
    proxy?.$modal.msgError(error?.message || '重新开始考试失败');
    throw error;
  } finally {
    restartingExam.value = false;
  }
};

const getList = async () => {
  loading.value = true;
  const res = await listCourseProgress(queryParams.value);
  progressList.value = res.rows;
  total.value = res.total;
  loading.value = false;
};

const loadSchoolOptions = async () => {
  const res = await listSchool({ pageNum: 1, pageSize: 9999 });
  schoolOptions.value = (res.rows || []).map((item) => ({
    ...item,
    cacheId: item.schoolId,
    sourceSchoolId: item.schoolId,
    displayLabel: item.schoolName,
    videoSupported: item.schoolVideo,
    workSupported: item.schoolWork,
    examSupported: item.schoolExam,
    examSpecialOrderRequired: item.schoolExam2,
    faceRequired: item.schoolFace,
    examType: item.schoolExamType,
    answerOk: item.schoolAnswerOk,
    examState: item.schoolExamState,
    submitTime: item.schoolSumbitTime,
    ipNumber: item.schoolIpNumber
  }));
};

const handleSchoolChange = (value: number) => {
  selectedSchool.value = schoolOptions.value.find((item) => item.cacheId === value);
};

const loadMatchedStudent = async (account: string, schoolId?: number) => {
  const studentRes = await listStudent({
    pageNum: 1,
    pageSize: 10,
    account,
    schoolId: schoolId ? String(schoolId) : undefined
  });
  return (studentRes.rows || []).find((item) => item.account === account && (!schoolId || item.schoolId === schoolId)) as EaStudentVO | undefined;
};

const openSubmitDialog = async () => {
  submitVisible.value = true;
  if (!schoolOptions.value.length) {
    await loadSchoolOptions();
  }
};

const resetSubmitForm = () => {
  submitFormRef.value?.resetFields();
  selectedSchool.value = undefined;
};

const submitOrder = () => {
  submitFormRef.value?.validate(async (valid: boolean) => {
    if (!valid) return;
    if (!selectedSchool.value) {
      proxy?.$modal.msgWarning('请选择学校');
      return;
    }
    const payload: EaStudentForm = {
      schoolId: selectedSchool.value.sourceSchoolId,
      account: submitForm.account.trim(),
      password: submitForm.password.trim(),
      name: '',
      status: 0
    };
    submitting.value = true;
    try {
      let student = await loadMatchedStudent(payload.account, selectedSchool.value.sourceSchoolId);
      try {
        if (!student) {
          await addStudent(payload);
        } else if (student.password !== payload.password) {
          await updateStudent({
            ...student,
            password: payload.password,
            name: cleanStudentName(student.name, student.account),
            status: student.status ?? 0
          });
        }
      } catch (error: any) {
        const message = String(error?.message || '');
        if (!message.includes('已存在该记录')) {
          throw error;
        }
      }
      student = await loadMatchedStudent(payload.account, selectedSchool.value.sourceSchoolId);
      let submittedOrder: EaOrderVO | undefined;
      if (student) {
        proxy?.$modal.msg('正在检测登录状态...');
        await checkStudentLogin({ studentId: String(student.studentId) });
        const orderPayload: EaOrderForm = {
          studentId: String(student.studentId),
          schoolId: String(selectedSchool.value.sourceSchoolId),
          platformId: String(selectedSchool.value.platformId),
          orderType: 1,
          courseName: '',
          term: '',
          status: 0,
          costPoints: 0,
          remark: '课程进度页提交订单'
        };
        await addOrder(orderPayload);
        const orderRes = await listOrder({ pageNum: 1, pageSize: 1, studentId: String(student.studentId) });
        submittedOrder = (orderRes.rows || [])[0];
      }
      proxy?.$modal.msgSuccess(submittedOrder?.orderId ? '信息获取成功，任务已进入执行队列' : '信息获取成功，任务生成后将自动执行');
      queryParams.value.pageNum = 1;
      queryParams.value.courseName = '';
      queryParams.value.studentAccount = '';
      queryParams.value.term = '';
      await getList();
      submitVisible.value = false;
      resetSubmitForm();
    } catch (error) {
      await getList();
      console.error(error);
    } finally {
      submitting.value = false;
    }
  });
};

const handleQuery = () => {
  queryParams.value.pageNum = 1;
  getList();
};

const resetQuery = () => {
  queryFormRef.value?.resetFields();
  handleQuery();
};

const handleDetail = async (row: EaCourseProgressVO) => {
  detailVisible.value = true;
  detailTab.value = 'course';
  debugTab.value = 'video';
  detailLoading.value = true;
  try {
    await loadOrderDetail(row);
  } finally {
    detailLoading.value = false;
  }
};

onMounted(async () => {
  if (route.query.openSubmit === '1') {
    await openSubmitDialog();
    await router.replace({ path: route.path, query: {} });
  }
  getList();
});
</script>

<style scoped>
.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.toolbar-tip {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.toolbar-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.course-info {
  color: #374151;
  line-height: 1.4;
}

.quick-submit-form {
  position: relative;
}

.quick-submit-form :deep(.el-select) {
  width: 100%;
}

.autofill-decoys {
  position: absolute;
  top: -1000px;
  left: -1000px;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}

.school-strip {
  margin-top: 4px;
  padding: 12px;
  border: 1px solid #dbeafe;
  border-radius: 6px;
  background: #eff6ff;
  font-size: 13px;
  color: #4b5563;
}

.school-name {
  font-weight: 600;
  color: #1f2937;
}

.school-support-grid {
  display: grid;
  grid-template-columns: repeat(2, max-content minmax(54px, max-content));
  gap: 8px 10px;
  align-items: center;
  margin-top: 10px;
}

.progress-tags {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
}

.detail-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.detail-action-tip {
  color: #6b7280;
  font-size: 13px;
}

.detail-action-buttons {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  gap: 8px;
}

.order-summary :deep(.el-descriptions__label) {
  min-width: 92px;
  white-space: nowrap;
}

.task-status-alert {
  margin-bottom: 14px;
}

.task-status-meta {
  margin-left: 12px;
  color: #6b7280;
  font-weight: 400;
}

.task-last-error {
  margin-top: 6px;
  color: #b91c1c;
  line-height: 1.5;
  word-break: break-word;
}

.debug-collapse {
  margin-top: 20px;
}

.debug-tabs {
  padding-top: 4px;
}

.detail-table :deep(.el-table__cell) {
  word-break: normal;
}

.user-detail-tabs {
  margin-top: 18px;
}

.user-detail-tabs :deep(.el-tabs__content) {
  max-height: 420px;
  overflow: auto;
}

.user-detail-table {
  width: 100%;
}

.course-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
}

.course-cell__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.learning-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.learning-progress :deep(.el-progress) {
  flex: 1;
  min-width: 120px;
}

.learning-progress__text {
  min-width: 54px;
  color: #6b7280;
  font-size: 12px;
  text-align: right;
  white-space: nowrap;
}

@media (max-width: 1200px) {
  .progress-detail-dialog :deep(.el-dialog) {
    width: 92vw !important;
  }
}

@media (max-width: 768px) {
  .toolbar-row,
  .toolbar-actions,
  .detail-action-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .detail-action-buttons {
    flex-wrap: wrap;
  }

  .school-support-grid {
    grid-template-columns: max-content minmax(54px, max-content);
  }
}
</style>
