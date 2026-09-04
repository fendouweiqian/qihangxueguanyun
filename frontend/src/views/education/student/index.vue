<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="学校" prop="schoolId">
              <el-select v-model="queryParams.schoolId" placeholder="请选择学校" clearable style="width: 200px">
                <el-option v-for="item in schoolOptions" :key="item.schoolId" :label="item.schoolName" :value="item.schoolId"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="账号" prop="account">
              <el-input v-model="queryParams.account" placeholder="请输入账号" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="姓名" prop="name">
              <el-input v-model="queryParams.name" placeholder="请输入姓名" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="queryParams.phone" placeholder="请输入手机号" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="状态" prop="status">
              <el-select v-model="queryParams.status" placeholder="请选择状态" clearable style="width: 160px">
                <el-option label="正常" :value="0" />
                <el-option label="禁用" :value="1" />
              </el-select>
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
          <el-col :span="1.5">
            <el-button type="info" plain icon="Top" @click="handleImport">导入</el-button>
          </el-col>
          <right-toolbar v-model:show-search="showSearch" @query-table="getList"></right-toolbar>
        </el-row>
      </template>

      <el-table v-loading="loading" border :data="studentList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="学员ID" align="center" prop="studentId" width="110" />
        <el-table-column label="学校" align="center" min-width="180" :show-overflow-tooltip="true">
          <template #default="scope">
            <span>{{ schoolNameById(scope.row.schoolId) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="账号" align="center" prop="account" min-width="160" />
        <el-table-column label="OpenId" align="center" prop="openId" min-width="180" :show-overflow-tooltip="true" />
        <el-table-column label="姓名" align="center" width="120">
          <template #default="scope">
            <span>{{ studentDisplayName(scope.row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="年级" align="center" width="120">
          <template #default="scope">
            <span>{{ profileLabel(scope.row.studyGrade) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="专业" align="center" prop="major" min-width="160" :show-overflow-tooltip="true">
          <template #default="scope">
            <span>{{ profileLabel(scope.row.major) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="手机号" align="center" prop="phone" width="140" />
        <el-table-column label="状态" align="center" prop="status" width="80">
          <template #default="scope">
            <el-tag v-if="scope.row.status === 0" type="success">正常</el-tag>
            <el-tag v-else type="info">禁用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" align="center" prop="createTime" width="180" />
        <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="120">
          <template #default="scope">
            <el-tooltip content="图像" placement="top">
              <el-button link type="primary" icon="Picture" @click="handleFaceMedia(scope.row)"></el-button>
            </el-tooltip>
            <el-tooltip content="修改" placement="top">
              <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)"></el-button>
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)"></el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="640px" append-to-body>
      <el-form ref="studentFormRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="学校" prop="schoolId">
          <el-select v-model="form.schoolId" placeholder="请选择学校" style="width: 100%">
            <el-option v-for="item in schoolOptions" :key="item.schoolId" :label="item.schoolName" :value="item.schoolId"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="账号" prop="account">
          <el-input v-model="form.account" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" placeholder="请输入密码" type="password" show-password />
        </el-form-item>
        <el-form-item v-if="showOpenIdField" label="OpenId" prop="openId">
          <el-input v-model="form.openId" placeholder="请输入小程序open_id（可选）" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="学籍年级" prop="studyGrade">
          <el-input v-model="form.studyGrade" placeholder="请输入学籍年级" />
        </el-form-item>
        <el-form-item label="培养专业" prop="major">
          <el-input v-model="form.major" placeholder="请输入培养专业" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="身份证" prop="idCard">
          <el-input v-model="form.idCard" placeholder="请输入身份证" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态">
            <el-option label="正常" :value="0" />
            <el-option label="禁用" :value="1" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>

    <el-drawer v-model="faceDrawer.open" title="学员图像档案" size="680px">
      <div v-loading="faceDrawer.loading">
        <el-descriptions :column="1" border class="mb-4">
          <el-descriptions-item label="学员">{{ currentFaceStudentLabel }}</el-descriptions-item>
          <el-descriptions-item label="学校">{{ schoolNameById(faceDrawer.student?.schoolId) }}</el-descriptions-item>
        </el-descriptions>

        <el-upload
          ref="faceUploadRef"
          :limit="1"
          accept=".mp4"
          :headers="faceUpload.headers"
          :action="faceUpload.url"
          :data="{ studentId: faceDrawer.student?.studentId }"
          :disabled="faceUpload.isUploading || !faceDrawer.student?.studentId"
          :on-progress="handleFaceUploadProgress"
          :on-success="handleFaceUploadSuccess"
          :auto-upload="false"
          drag
          class="mb-4"
        >
          <el-icon class="el-icon--upload">
            <i-ep-upload-filled />
          </el-icon>
          <div class="el-upload__text">将人脸视频拖到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">仅允许上传 mp4 文件，上传后会归档到当前学员。</div>
          </template>
        </el-upload>

        <div class="face-actions mb-3">
          <el-button type="primary" icon="Upload" :disabled="!faceDrawer.student?.studentId || faceUpload.isUploading" @click="submitFaceUpload">
            上传
          </el-button>
          <el-button icon="Refresh" @click="loadFaceMediaList">刷新</el-button>
        </div>

        <el-table border :data="faceDrawer.list">
          <el-table-column label="文件地址" prop="fileUrl" min-width="260" :show-overflow-tooltip="true" />
          <el-table-column label="类型" prop="fileType" width="90" align="center" />
          <el-table-column label="状态" width="90" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.status === 1 ? 'success' : 'info'">{{ scope.row.status === 1 ? '可用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="上传时间" prop="createTime" width="180" align="center" />
          <el-table-column label="操作" width="90" align="center">
            <template #default="scope">
              <el-tooltip content="删除" placement="top">
                <el-button link type="danger" icon="Delete" @click="handleFaceDelete(scope.row)" />
              </el-tooltip>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>

    <el-dialog v-model="upload.open" :title="upload.title" width="480px" append-to-body>
      <el-form :model="upload" label-width="90px">
        <el-form-item label="学校">
          <el-select v-model="upload.schoolId" placeholder="请选择学校" style="width: 100%">
            <el-option v-for="item in schoolOptions" :key="item.schoolId" :label="item.schoolName" :value="item.schoolId"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <el-upload
        ref="uploadRef"
        :limit="1"
        accept=".xlsx, .xls"
        :headers="upload.headers"
        :action="upload.url"
        :data="{ schoolId: upload.schoolId }"
        :disabled="upload.isUploading"
        :on-progress="handleFileUploadProgress"
        :on-success="handleFileSuccess"
        :auto-upload="false"
        drag
      >
        <el-icon class="el-icon--upload">
          <i-ep-upload-filled />
        </el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="text-center el-upload__tip">
            <span>仅允许导入xls、xlsx格式文件。</span>
          </div>
        </template>
      </el-upload>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" :disabled="!upload.schoolId" @click="submitFileForm">确 定</el-button>
          <el-button @click="upload.open = false">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="EduStudent" lang="ts">
import { delFaceMedia, listFaceMedia } from '@/api/education/faceMedia';
import { addStudent, delStudent, fetchStudentName, getStudent, listStudent, updateStudent } from '@/api/education/student';
import { listSchool } from '@/api/education/school';
import { EaFaceMediaVO, EaSchoolVO, EaStudentForm, EaStudentQuery, EaStudentVO } from '@/api/education/types';
import { globalHeaders } from '@/utils/request';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const studentList = ref<EaStudentVO[]>([]);
const schoolOptions = ref<EaSchoolVO[]>([]);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref<Array<number | string>>([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();
const studentFormRef = ref<ElFormInstance>();
const uploadRef = ref<ElUploadInstance>();
const faceUploadRef = ref<ElUploadInstance>();

const dialog = reactive<DialogOption>({
  visible: false,
  title: ''
});

const upload = reactive<ImportOption>({
  open: false,
  title: '学员导入',
  isUploading: false,
  headers: globalHeaders(),
  url: import.meta.env.VITE_APP_BASE_API + '/education/student/import',
  schoolId: undefined
});

const faceDrawer = reactive({
  open: false,
  loading: false,
  student: undefined as EaStudentVO | undefined,
  list: [] as EaFaceMediaVO[]
});

const faceUpload = reactive<ImportOption>({
  open: false,
  title: '上传学员图像',
  isUploading: false,
  headers: globalHeaders(),
  url: import.meta.env.VITE_APP_BASE_API + '/education/face-media/upload'
});

const initFormData: EaStudentForm = {
  studentId: undefined,
  schoolId: undefined,
  account: '',
  password: '',
  openId: '',
  name: '',
  studyGrade: '',
  major: '',
  phone: '',
  idCard: '',
  status: 0
};

const containsChinese = (value?: string) => /[\u4e00-\u9fff]/.test(String(value || ''));

function validateStudentName(_rule: unknown, value: string, callback: (error?: Error) => void) {
  const name = String(value || '').trim();
  const account = String(form.value.account || '').trim();
  if (name && (name === account || !containsChinese(name))) {
    callback(new Error('请输入学生中文姓名，不能填写账号'));
    return;
  }
  callback();
}

const data = reactive<PageData<EaStudentForm, EaStudentQuery>>({
  form: { ...initFormData },
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    schoolId: undefined,
    account: '',
    name: '',
    phone: '',
    status: undefined
  },
  rules: {
    schoolId: [{ required: true, message: '学校不能为空', trigger: 'change' }],
    account: [{ required: true, message: '账号不能为空', trigger: 'blur' }],
    password: [{ required: true, message: '密码不能为空', trigger: 'blur' }],
    name: [{ validator: validateStudentName, trigger: 'blur' }]
  }
});

const { queryParams, form, rules } = toRefs(data);

const isOpenIdRequiredBySchool = (school?: EaSchoolVO) => {
  if (!school) {
    return false;
  }
  const schoolName = String(school.schoolName || '').toLowerCase();
  const schoolUrl = String(school.schoolUrl || '').toLowerCase();
  const accessAddress = String(school.accessAddress || '').toLowerCase();
  return (
    school.accessType === 2 ||
    schoolName.includes('成考云') ||
    schoolUrl.includes('chengkaoyun') ||
    accessAddress.includes('成人教育学生平台') ||
    accessAddress.includes('成考云')
  );
};

const showOpenIdField = computed(() => {
  const schoolId = form.value.schoolId;
  if (schoolId === undefined || schoolId === null || schoolId === '') {
    return false;
  }
  const selectedSchool = schoolOptions.value.find((item) => String(item.schoolId) === String(schoolId));
  return isOpenIdRequiredBySchool(selectedSchool);
});

const studentDisplayName = (student?: EaStudentVO) => {
  const name = String(student?.name || '').trim();
  const account = String(student?.account || '').trim();
  if (!name || name === account || !containsChinese(name)) {
    return '-';
  }
  return name;
};

const profileLabel = (value?: string) => String(value || '').trim() || '-';

const currentFaceStudentLabel = computed(() => {
  const student = faceDrawer.student;
  if (!student) {
    return '-';
  }
  const name = studentDisplayName(student);
  return name === '-' ? `${student.account}` : `${name}（${student.account}）`;
});

const schoolNameById = (schoolId?: number | string) => {
  if (schoolId === undefined || schoolId === null || schoolId === '') {
    return '-';
  }
  return schoolOptions.value.find((item) => String(item.schoolId) === String(schoolId))?.schoolName || String(schoolId);
};

const getSchoolOptions = async () => {
  const res = await listSchool({ pageNum: 1, pageSize: 9999 });
  schoolOptions.value = res.rows || [];
};

const getList = async () => {
  loading.value = true;
  const res = await listStudent(queryParams.value);
  studentList.value = res.rows;
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

const handleSelectionChange = (selection: EaStudentVO[]) => {
  ids.value = selection.map((item) => item.studentId);
  single.value = selection.length !== 1;
  multiple.value = !selection.length;
};

const reset = () => {
  form.value = { ...initFormData };
  studentFormRef.value?.resetFields();
};

const cancel = () => {
  reset();
  dialog.visible = false;
};

const handleAdd = async () => {
  reset();
  await getSchoolOptions();
  dialog.visible = true;
  dialog.title = '新增学员';
};

const handleUpdate = async (row?: EaStudentVO) => {
  reset();
  await getSchoolOptions();
  const studentId = row?.studentId || ids.value[0];
  const { data } = await getStudent(studentId);
  Object.assign(form.value, data);
  dialog.visible = true;
  dialog.title = '修改学员';
};

const submitForm = async () => {
  if (!studentFormRef.value) {
    return;
  }

  try {
    if (!form.value.studentId) {
      await studentFormRef.value.validateField(['schoolId', 'account', 'password']);
      try {
        const res = await fetchStudentName({
          schoolId: form.value.schoolId,
          account: form.value.account,
          password: form.value.password,
          openId: form.value.openId
        });
        const fetchedName = (res.data?.name || '').trim();
        const validated = res.data?.validated !== false;
        if (!validated) {
          ElMessage.error('账号校验失败，请确认账号信息是否正确');
          return;
        }
        if (fetchedName) {
          form.value.name = fetchedName;
        } else if (!String(form.value.name || '').trim()) {
          ElMessage.warning('该平台仅完成账号校验，请手动填写学员姓名');
          return;
        }
      } catch {
        ElMessage.error('获取信息失败，请确认账号信息是否正确');
        return;
      }
    }

    await studentFormRef.value.validate();
    if (form.value.studentId) {
      await updateStudent(form.value);
    } else {
      await addStudent(form.value);
    }
    proxy?.$modal.msgSuccess('操作成功');
    dialog.visible = false;
    await getList();
  } catch {
    // Validation errors are displayed by the form itself.
  }
};

const handleDelete = async (row?: EaStudentVO) => {
  const studentIds = row?.studentId || ids.value;
  await proxy?.$modal.confirm('是否确认删除学员编号为"' + studentIds + '"的数据项？');
  await delStudent(studentIds);
  await getList();
  proxy?.$modal.msgSuccess('删除成功');
};

const loadFaceMediaList = async () => {
  if (!faceDrawer.student?.studentId) {
    faceDrawer.list = [];
    return;
  }
  faceDrawer.loading = true;
  try {
    const res = await listFaceMedia({
      pageNum: 1,
      pageSize: 20,
      studentId: faceDrawer.student.studentId
    });
    faceDrawer.list = res.rows || [];
  } finally {
    faceDrawer.loading = false;
  }
};

const handleFaceMedia = async (row: EaStudentVO) => {
  faceDrawer.student = row;
  faceDrawer.open = true;
  faceUploadRef.value?.clearFiles();
  await loadFaceMediaList();
};

const handleFaceUploadProgress = () => {
  faceUpload.isUploading = true;
};

const handleFaceUploadSuccess = async () => {
  faceUpload.isUploading = false;
  faceUploadRef.value?.clearFiles();
  proxy?.$modal.msgSuccess('上传成功');
  await loadFaceMediaList();
};

const submitFaceUpload = () => {
  faceUploadRef.value?.submit();
};

const handleFaceDelete = async (row: EaFaceMediaVO) => {
  await proxy?.$modal.confirm('是否确认删除图像记录编号为"' + row.faceMediaId + '"的数据项？');
  await delFaceMedia(row.faceMediaId);
  await loadFaceMediaList();
  proxy?.$modal.msgSuccess('删除成功');
};

const handleImport = async () => {
  upload.open = true;
  upload.schoolId = undefined;
  await getSchoolOptions();
};

const handleFileUploadProgress = () => {
  upload.isUploading = true;
};

const handleFileSuccess = (response: any, file: UploadFile) => {
  upload.open = false;
  upload.isUploading = false;
  uploadRef.value?.handleRemove(file);
  ElMessageBox.alert("<div style='overflow: auto;overflow-x: hidden;max-height: 70vh;padding: 10px 20px 0;'>" + response.msg + '</div>', '导入结果', {
    dangerouslyUseHTMLString: true
  });
  getList();
};

const submitFileForm = () => {
  uploadRef.value?.submit();
};

onMounted(async () => {
  await getSchoolOptions();
  getList();
});
</script>

<style scoped>
.face-actions {
  display: flex;
  gap: 8px;
}
</style>
