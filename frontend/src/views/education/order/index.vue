<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="订单ID" prop="orderId">
              <el-input v-model="queryParams.orderId" placeholder="请输入订单ID" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="学员" prop="studentId">
              <el-select v-model="queryParams.studentId" placeholder="请选择学员" clearable style="width: 200px">
                <el-option v-for="item in studentOptions" :key="item.studentId" :label="studentLabel(item)" :value="item.studentId" />
              </el-select>
            </el-form-item>
            <el-form-item label="学校" prop="schoolId">
              <el-select v-model="queryParams.schoolId" placeholder="请选择学校" clearable style="width: 220px">
                <el-option v-for="item in schoolOptions" :key="item.schoolId" :label="item.schoolName" :value="item.schoolId" />
              </el-select>
            </el-form-item>
            <el-form-item label="平台" prop="platformId">
              <el-select v-model="queryParams.platformId" placeholder="请选择平台" clearable style="width: 200px">
                <el-option v-for="item in platformOptions" :key="item.platformId" :label="item.platformName" :value="item.platformId" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态" prop="status">
              <el-input v-model="queryParams.status" placeholder="状态" clearable style="width: 120px" />
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
        <el-row :gutter="10" class="mb8">
          <el-col :span="1.5">
            <el-button type="primary" plain icon="Plus" @click="handleAdd">新增</el-button>
          </el-col>
          <el-col :span="1.5">
            <el-button type="success" plain icon="Edit" :disabled="single" @click="handleUpdate()">修改</el-button>
          </el-col>
          <el-col :span="1.5">
            <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete()">删除</el-button>
          </el-col>
          <right-toolbar v-model:show-search="showSearch" @query-table="getList" />
        </el-row>
      </template>

      <el-table v-loading="loading" border :data="orderList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="订单ID" align="center" prop="orderId" min-width="170" />
        <el-table-column label="学员" align="center" min-width="160">
          <template #default="scope">
            <span>{{ studentNameById(scope.row.studentId) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="课程" align="center" min-width="180" :show-overflow-tooltip="true">
          <template #default="scope">
            <span>{{ orderCourseLabel(scope.row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="平台" align="center" min-width="120">
          <template #default="scope">
            <span>{{ platformNameById(scope.row.platformId) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" align="center" width="90">
          <template #default="scope">
            <el-tag :type="orderStatusTag(scope.row.status)">{{ orderStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="扣费积分" align="center" prop="costPoints" width="100" />
        <el-table-column label="创建时间" align="center" prop="createTime" width="180" />
        <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="170">
          <template #default="scope">
            <el-tooltip content="详情" placement="top">
              <el-button link type="primary" icon="View" @click="handleDetail(scope.row)" />
            </el-tooltip>
            <el-tooltip content="修改" placement="top">
              <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" />
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <el-button link type="danger" icon="Delete" @click="handleDelete(scope.row)" />
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="760px" append-to-body>
      <el-form ref="orderFormRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="学员" prop="studentId">
              <el-select v-model="form.studentId" placeholder="请选择学员" style="width: 100%">
                <el-option v-for="item in studentOptions" :key="item.studentId" :label="studentLabel(item)" :value="item.studentId" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学校" prop="schoolId">
              <el-select v-model="form.schoolId" placeholder="请选择学校" style="width: 100%">
                <el-option v-for="item in schoolOptions" :key="item.schoolId" :label="item.schoolName" :value="item.schoolId" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="平台" prop="platformId">
              <el-select v-model="form.platformId" placeholder="请选择平台" style="width: 100%">
                <el-option v-for="item in platformOptions" :key="item.platformId" :label="item.platformName" :value="item.platformId" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="订单类型" prop="orderType">
              <el-input-number v-model="form.orderType" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="课程名称" prop="courseName">
              <el-input v-model="form.courseName" placeholder="请输入课程名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="课程编码" prop="courseCode">
              <el-input v-model="form.courseCode" placeholder="请输入课程编码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学期" prop="term">
              <el-input v-model="form.term" placeholder="请输入学期" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="扣费积分" prop="costPoints">
              <el-input-number v-model="form.costPoints" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="考试开始" prop="examStartAt">
              <el-date-picker v-model="form.examStartAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="考试结束" prop="examEndAt">
              <el-date-picker v-model="form.examEndAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注" prop="remark">
              <el-input v-model="form.remark" placeholder="请输入备注" type="textarea" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="订单执行详情" size="72%">
      <div v-loading="detailLoading">
        <el-empty v-if="!detail.order" description="暂无订单详情" />
        <template v-else>
          <el-descriptions :column="2" border class="mb-4 order-summary">
            <el-descriptions-item label="订单ID">{{ detail.order.orderId || '-' }}</el-descriptions-item>
            <el-descriptions-item label="订单状态">
              <el-tag :type="orderStatusTag(detail.order.status)">{{ orderStatusLabel(detail.order.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="学员">{{ studentLabel(detail.student) }}</el-descriptions-item>
            <el-descriptions-item label="课程">{{ detailCourseLabel }}</el-descriptions-item>
            <el-descriptions-item label="平台">{{ detail.platform?.platformName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="学期">{{ termLabel(detail.order.term || detail.courseProgress?.term) }}</el-descriptions-item>
            <el-descriptions-item label="扣费积分">{{ detail.order.costPoints ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="备注" :span="2">{{ detail.order.remark || '-' }}</el-descriptions-item>
          </el-descriptions>

          <div class="progress-panel mb-4">
            <div v-for="item in progressCards" :key="item.key" class="progress-card" :class="`progress-card--${item.key}`">
              <div class="progress-card__header">
                <span class="progress-card__title">{{ item.title }}</span>
                <el-tag :type="progressStatusTag(item.status)" effect="light">{{ item.statusLabel }}</el-tag>
              </div>
              <div class="progress-card__time">{{ item.time || '-' }}</div>
              <div class="progress-card__note">{{ item.note || '-' }}</div>
            </div>
          </div>

          <el-tabs v-model="detailTab" class="detail-tabs">
            <el-tab-pane label="学习执行明细" name="video">
              <el-table border :data="videoTimeline" class="detail-table">
                <el-table-column label="时间" align="center" prop="time" width="180" />
                <el-table-column label="状态" align="center" width="110">
                  <template #default="scope">
                    <el-tag :type="progressStatusTag(scope.row.status)">{{ progressStatusLabel(scope.row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="进度内容" prop="content" min-width="620" :show-overflow-tooltip="true" />
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="作业执行明细" name="work">
              <el-table border :data="workTimeline" class="detail-table">
                <el-table-column label="时间" align="center" prop="time" width="180" />
                <el-table-column label="状态" align="center" width="110">
                  <template #default="scope">
                    <el-tag :type="progressStatusTag(scope.row.status)">{{ progressStatusLabel(scope.row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="进度内容" prop="content" min-width="620" :show-overflow-tooltip="true" />
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="考试执行明细" name="exam">
              <el-table border :data="examTimeline" class="detail-table">
                <el-table-column label="时间" align="center" prop="time" width="180" />
                <el-table-column label="状态" align="center" width="110">
                  <template #default="scope">
                    <el-tag :type="progressStatusTag(scope.row.status)">{{ progressStatusLabel(scope.row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="进度内容" prop="content" min-width="620" :show-overflow-tooltip="true" />
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup name="EduOrder" lang="ts">
import { addOrder, delOrder, getOrder, getOrderDetail, listOrder, updateOrder } from '@/api/education/order';
import { listPlatform } from '@/api/education/platform';
import { listSchool } from '@/api/education/school';
import { listStudent } from '@/api/education/student';
import { EaOrderDetailVO, EaOrderForm, EaOrderQuery, EaOrderVO, EaPlatformVO, EaSchoolVO, EaStudentVO } from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const orderList = ref<EaOrderVO[]>([]);
const platformOptions = ref<EaPlatformVO[]>([]);
const schoolOptions = ref<EaSchoolVO[]>([]);
const studentOptions = ref<EaStudentVO[]>([]);
const loading = ref(true);
const detailLoading = ref(false);
const detailVisible = ref(false);
const showSearch = ref(true);
const detailTab = ref('video');
const ids = ref<Array<number | string>>([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();
const orderFormRef = ref<ElFormInstance>();

const dialog = reactive<DialogOption>({
  visible: false,
  title: ''
});

const detail = ref<EaOrderDetailVO>({});

type LogBizType = 'VIDEO' | 'WORK' | 'EXAM' | 'SYSTEM';

const initFormData: EaOrderForm = {
  orderId: undefined,
  studentId: undefined,
  schoolId: undefined,
  platformId: undefined,
  orderType: 0,
  courseName: '',
  courseCode: '',
  term: '',
  examStartAt: '',
  examEndAt: '',
  costPoints: 0,
  remark: ''
};

const data = reactive<PageData<EaOrderForm, EaOrderQuery>>({
  form: { ...initFormData },
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    orderId: undefined,
    studentId: undefined,
    schoolId: undefined,
    platformId: undefined,
    status: undefined
  },
  rules: {
    studentId: [{ required: true, message: '学员不能为空', trigger: 'change' }],
    schoolId: [{ required: true, message: '学校不能为空', trigger: 'change' }],
    platformId: [{ required: true, message: '平台不能为空', trigger: 'change' }],
    orderType: [{ required: true, message: '订单类型不能为空', trigger: 'blur' }],
    costPoints: [{ required: true, message: '扣费积分不能为空', trigger: 'blur' }]
  }
});

const { queryParams, form, rules } = toRefs(data);

const loadOptions = async () => {
  const [platformRes, schoolRes, studentRes] = await Promise.all([
    listPlatform({ pageNum: 1, pageSize: 9999 }),
    listSchool({ pageNum: 1, pageSize: 9999 }),
    listStudent({ pageNum: 1, pageSize: 9999 })
  ]);
  platformOptions.value = platformRes.rows || [];
  schoolOptions.value = schoolRes.rows || [];
  studentOptions.value = studentRes.rows || [];
};

const studentLabel = (student?: EaStudentVO) => {
  if (!student) {
    return '-';
  }
  const name = studentDisplayName(student);
  const account = String(student.account || '').trim();
  if (name !== '-' && account) {
    return `${name} / ${account}`;
  }
  return name !== '-' ? name : account || '-';
};

const containsChinese = (value?: string) => /[\u4e00-\u9fff]/.test(String(value || ''));

const studentDisplayName = (student?: EaStudentVO) => {
  const name = String(student?.name || '').trim();
  const account = String(student?.account || '').trim();
  if (!name || name === account || !containsChinese(name)) {
    return '-';
  }
  return name;
};

const studentNameById = (studentId?: number) => {
  const student = studentOptions.value.find((item) => item.studentId === studentId);
  return studentLabel(student);
};

const schoolNameById = (schoolId?: number) => {
  return schoolOptions.value.find((item) => item.schoolId === schoolId)?.schoolName || '-';
};

const rawSchoolNameById = (schoolId?: number) => {
  return schoolOptions.value.find((item) => item.schoolId === schoolId)?.schoolName || '';
};

const platformNameById = (platformId?: number) => {
  return platformOptions.value.find((item) => item.platformId === platformId)?.platformName || '-';
};

const courseLabel = (courseName?: string, schoolName?: string) => {
  const courseText = String(courseName || '').trim();
  const schoolText = String(schoolName || '').trim();
  if (courseText && schoolText && courseText !== schoolText) {
    return `${courseText} / ${schoolText}`;
  }
  return courseText || schoolText || '-';
};

const orderCourseLabel = (order: EaOrderVO) => courseLabel(order.courseName, rawSchoolNameById(order.schoolId));

const detailCourseLabel = computed(() => courseLabel(detail.value.order?.courseName, detail.value.school?.schoolName));

const termLabel = (term?: string) => String(term || '').trim() || '未返回';

const orderStatusLabel = (status?: number) => {
  if (status === 2) {
    return '已完成';
  }
  if (status === 3) {
    return '失败';
  }
  if (status === 1) {
    return '执行中';
  }
  return '待执行';
};

const orderStatusTag = (status?: number) => {
  if (status === 2) {
    return 'success';
  }
  if (status === 3) {
    return 'danger';
  }
  if (status === 1) {
    return 'warning';
  }
  return 'info';
};

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

const progressCardStatusLabel = (key: string, status?: number) => {
  if (key === 'exam' && (status || 0) === 0) {
    return '考试未开始';
  }
  return progressStatusLabel(status);
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

const stripAnsi = (value?: string) => (value || '').replace(/\x1B\[[0-9;]*m/g, '');

const resolveBizType = (log: { bizType?: string }, message: string): LogBizType => {
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

const progressCards = computed(() => {
  const progress = detail.value.courseProgress;
  const exam = detail.value.examProgress;
  return [
    {
      key: 'video',
      title: '视频学习',
      status: progress?.videoStatus,
      time: progress?.videoTime || progress?.updateTime,
      note: progress?.videoNote,
      statusLabel: progressCardStatusLabel('video', progress?.videoStatus)
    },
    {
      key: 'work',
      title: '作业进度',
      status: progress?.workStatus,
      time: progress?.workTime,
      note: progress?.workNote,
      statusLabel: progressCardStatusLabel('work', progress?.workStatus)
    },
    {
      key: 'exam',
      title: '考试进度',
      status: progress?.examStatus,
      time: progress?.examTime || exam?.finishedAt,
      note: progress?.examNote || exam?.note || '考试未开始',
      statusLabel: progressCardStatusLabel('exam', progress?.examStatus)
    }
  ];
});

const timelineRows = computed(() => {
  const logs = detail.value.logs || [];
  return logs.filter((log) => (log.bizStatus || 0) > 0).map((log, index) => {
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

const videoTimeline = computed(() => timelineByType('VIDEO'));
const workTimeline = computed(() => timelineByType('WORK'));
const examTimeline = computed(() => timelineByType('EXAM'));

const getList = async () => {
  loading.value = true;
  const res = await listOrder(queryParams.value);
  orderList.value = res.rows;
  total.value = res.total;
  loading.value = false;
};

const handleQuery = () => {
  queryParams.value.pageNum = 1;
  getList();
};

const resetQuery = () => {
  queryFormRef.value?.resetFields();
  handleQuery();
};

const handleSelectionChange = (selection: EaOrderVO[]) => {
  ids.value = selection.map((item) => item.orderId);
  single.value = selection.length !== 1;
  multiple.value = !selection.length;
};

const reset = () => {
  form.value = { ...initFormData };
  orderFormRef.value?.resetFields();
};

const cancel = () => {
  reset();
  dialog.visible = false;
};

const handleAdd = async () => {
  reset();
  await loadOptions();
  dialog.visible = true;
  dialog.title = '新增订单';
};

const handleUpdate = async (row?: EaOrderVO) => {
  reset();
  await loadOptions();
  const orderId = row?.orderId || ids.value[0];
  const { data } = await getOrder(orderId);
  Object.assign(form.value, data);
  dialog.visible = true;
  dialog.title = '修改订单';
};

const handleDetail = async (row: EaOrderVO) => {
  detailVisible.value = true;
  detailTab.value = 'video';
  detailLoading.value = true;
  try {
    const { data } = await getOrderDetail(row.orderId);
    detail.value = data || {};
  } finally {
    detailLoading.value = false;
  }
};

const submitForm = () => {
  orderFormRef.value?.validate(async (valid: boolean) => {
    if (valid) {
      if (form.value.orderId) {
        await updateOrder(form.value);
      } else {
        await addOrder(form.value);
      }
      proxy?.$modal.msgSuccess('操作成功');
      dialog.visible = false;
      await getList();
    }
  });
};

const handleDelete = async (row?: EaOrderVO) => {
  const orderIds = row?.orderId || ids.value;
  await proxy?.$modal.confirm('是否确认删除所选订单？');
  await delOrder(orderIds);
  await getList();
  proxy?.$modal.msgSuccess('删除成功');
};

onMounted(async () => {
  await loadOptions();
  getList();
});
</script>

<style scoped>
.order-summary :deep(.el-descriptions__label) {
  min-width: 92px;
  white-space: nowrap;
}

.progress-panel {
  display: grid;
  grid-template-columns: repeat(3, minmax(240px, 1fr));
  gap: 14px;
}

.progress-card {
  min-height: 132px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.progress-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.progress-card__title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.progress-card__time {
  margin-bottom: 10px;
  font-size: 13px;
  color: #6b7280;
}

.progress-card__note {
  font-size: 13px;
  color: #374151;
  line-height: 1.6;
  word-break: break-word;
}

.progress-card--video {
  border-top: 3px solid #67c23a;
}

.progress-card--work {
  border-top: 3px solid #409eff;
}

.progress-card--exam {
  border-top: 3px solid #909399;
}

.detail-tabs {
  padding: 4px 2px 0;
}

.detail-table :deep(.el-table__cell) {
  word-break: normal;
}

@media (max-width: 1200px) {
  .progress-panel {
    grid-template-columns: 1fr;
  }
}
</style>
