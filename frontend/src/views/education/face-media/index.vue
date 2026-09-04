<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="学员ID" prop="studentId">
              <el-input v-model="queryParams.studentId" placeholder="请输入学员ID" clearable @keyup.enter="handleQuery" />
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
            <el-button type="primary" plain icon="Upload" @click="handleUpload">上传视频</el-button>
          </el-col>
          <el-col :span="1.5">
            <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete()">删除</el-button>
          </el-col>
          <right-toolbar v-model:show-search="showSearch" @query-table="getList"></right-toolbar>
        </el-row>
      </template>

      <el-table v-loading="loading" border :data="faceList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="人脸ID" align="center" prop="faceMediaId" width="110" />
        <el-table-column label="学员ID" align="center" prop="studentId" width="110" />
        <el-table-column label="文件地址" align="center" prop="fileUrl" min-width="220" :show-overflow-tooltip="true" />
        <el-table-column label="文件类型" align="center" prop="fileType" width="100" />
        <el-table-column label="状态" align="center" prop="status" width="80" />
        <el-table-column label="上传人" align="center" prop="uploadedBy" width="110" />
        <el-table-column label="创建时间" align="center" prop="createTime" width="180" />
        <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="120">
          <template #default="scope">
            <el-tooltip content="删除" placement="top">
              <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)"></el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>

    <el-dialog v-model="upload.open" :title="upload.title" width="520px" append-to-body>
      <el-form :model="upload" label-width="90px">
        <el-form-item label="学员ID">
          <el-input v-model="upload.studentId" placeholder="请输入学员ID" />
        </el-form-item>
      </el-form>
      <el-upload
        ref="uploadRef"
        :limit="1"
        accept=".mp4"
        :headers="upload.headers"
        :action="upload.url"
        :data="{ studentId: upload.studentId }"
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
            <span>仅允许上传 mp4 文件。</span>
          </div>
        </template>
      </el-upload>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" :disabled="!upload.studentId" @click="submitFileForm">确 定</el-button>
          <el-button @click="upload.open = false">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="EduFaceMedia" lang="ts">
import { delFaceMedia, listFaceMedia } from '@/api/education/faceMedia';
import { EaFaceMediaQuery, EaFaceMediaVO } from '@/api/education/types';
import { globalHeaders } from '@/utils/request';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const faceList = ref<EaFaceMediaVO[]>([]);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref<Array<number | string>>([]);
const multiple = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();
const uploadRef = ref<ElUploadInstance>();

const upload = reactive<ImportOption>({
  open: false,
  title: '上传人脸视频',
  isUploading: false,
  headers: globalHeaders(),
  url: import.meta.env.VITE_APP_BASE_API + '/education/face-media/upload',
  studentId: undefined
});

const data = reactive<PageData<EaFaceMediaVO, EaFaceMediaQuery>>({
  form: {} as EaFaceMediaVO,
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    studentId: undefined,
    status: undefined
  },
  rules: {}
});

const { queryParams } = toRefs(data);

const getList = async () => {
  loading.value = true;
  const res = await listFaceMedia(queryParams.value);
  faceList.value = res.rows;
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

const handleSelectionChange = (selection: EaFaceMediaVO[]) => {
  ids.value = selection.map((item) => item.faceMediaId);
  multiple.value = !selection.length;
};

const handleUpload = () => {
  upload.open = true;
  upload.studentId = undefined;
};

const handleDelete = async (row?: EaFaceMediaVO) => {
  const faceMediaIds = row?.faceMediaId || ids.value;
  await proxy?.$modal.confirm('是否确认删除人脸记录编号为"' + faceMediaIds + '"的数据项？');
  await delFaceMedia(faceMediaIds);
  await getList();
  proxy?.$modal.msgSuccess('删除成功');
};

const handleFileUploadProgress = () => {
  upload.isUploading = true;
};

const handleFileSuccess = () => {
  upload.open = false;
  upload.isUploading = false;
  uploadRef.value?.clearFiles();
  proxy?.$modal.msgSuccess('上传成功');
  getList();
};

const submitFileForm = () => {
  uploadRef.value?.submit();
};

onMounted(() => {
  getList();
});
</script>
