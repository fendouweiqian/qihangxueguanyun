<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="租户编号" prop="tenantId">
              <el-input v-model="queryParams.tenantId" placeholder="请输入租户编号" clearable @keyup.enter="handleQuery" />
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
            <el-button type="primary" plain icon="Plus" @click="handleAdd">充值</el-button>
          </el-col>
          <right-toolbar v-model:show-search="showSearch" @query-table="getList"></right-toolbar>
        </el-row>
      </template>

      <el-table v-loading="loading" border :data="rechargeList">
        <el-table-column label="充值ID" align="center" prop="rechargeId" width="110" />
        <el-table-column label="租户" align="center" prop="tenantId" width="120" />
        <el-table-column label="操作人" align="center" prop="operatorUserId" width="110" />
        <el-table-column label="充值积分" align="center" prop="rechargePoints" width="100" />
        <el-table-column label="赠送积分" align="center" prop="giftPoints" width="100" />
        <el-table-column label="备注" align="center" prop="remark" min-width="160" :show-overflow-tooltip="true" />
        <el-table-column label="创建时间" align="center" prop="createTime" width="180" />
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="520px" append-to-body>
      <el-form ref="rechargeFormRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="租户编号" prop="tenantId">
          <el-input v-model="form.tenantId" placeholder="请输入租户编号" />
        </el-form-item>
        <el-form-item label="充值积分" prop="rechargePoints">
          <el-input-number v-model="form.rechargePoints" :min="0" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="赠送积分" prop="giftPoints">
          <el-input-number v-model="form.giftPoints" :min="0" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" placeholder="请输入备注" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="EduRecharge" lang="ts">
import { addRecharge, listRecharge } from '@/api/education/recharge';
import { EaRechargeForm, EaRechargeQuery, EaRechargeVO } from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const rechargeList = ref<EaRechargeVO[]>([]);
const loading = ref(true);
const showSearch = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();
const rechargeFormRef = ref<ElFormInstance>();

const dialog = reactive<DialogOption>({
  visible: false,
  title: ''
});

const initFormData: EaRechargeForm = {
  tenantId: '',
  rechargePoints: 0,
  giftPoints: 0,
  remark: ''
};

const data = reactive<PageData<EaRechargeForm, EaRechargeQuery>>({
  form: { ...initFormData },
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    tenantId: ''
  },
  rules: {
    tenantId: [{ required: true, message: '租户编号不能为空', trigger: 'blur' }],
    rechargePoints: [{ required: true, message: '充值积分不能为空', trigger: 'blur' }]
  }
});

const { queryParams, form, rules } = toRefs(data);

const getList = async () => {
  loading.value = true;
  const res = await listRecharge(queryParams.value);
  rechargeList.value = res.rows;
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

const reset = () => {
  form.value = { ...initFormData };
  rechargeFormRef.value?.resetFields();
};

const cancel = () => {
  reset();
  dialog.visible = false;
};

const handleAdd = () => {
  reset();
  dialog.visible = true;
  dialog.title = '租户充值';
};

const submitForm = () => {
  rechargeFormRef.value?.validate(async (valid: boolean) => {
    if (valid) {
      await addRecharge(form.value);
      proxy?.$modal.msgSuccess('充值成功');
      dialog.visible = false;
      await getList();
    }
  });
};

onMounted(() => {
  getList();
});
</script>
