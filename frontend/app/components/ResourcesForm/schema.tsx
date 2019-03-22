import {number} from "yup";

export const schema = {
  VCPUsAtStartup: number().integer().min(1).max(32).required(),
  coresPerSocket: number().required().label("VCPU cores per socket").required().test(
    "vcpus-multiplier-cores", "Number of cores should be a multiplier of number of cores per socket",
    function (value) {
      return this.parent.VCPUsAtStartup % value === 0;
    }
  ),
  ram: number().integer().min(256).max(1572864).required(),
};
