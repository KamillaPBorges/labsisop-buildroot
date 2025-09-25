#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/sched.h>
#include <linux/sched/signal.h>   /* for_each_process */
#include <linux/syscalls.h>
#include <linux/uaccess.h>        /* copy_to_user */
#include "sleeplist.h"

/* Retorna a contagem total de processos em sleep.
 * Copia até 'max' itens para 'ubuf' (se ubuf != NULL).
 * Estados considerados sleep: S (TASK_INTERRUPTIBLE = 1) e D (TASK_UNINTERRUPTIBLE = 2).
 */
asmlinkage long sys_listSleepProcs(struct sleep_proc __user *ubuf, int max)
{
    long total = 0;
    struct task_struct *p;

    if (max < 0) return -EINVAL;

    rcu_read_lock();
    for_each_process(p) {
        long st = READ_ONCE(p->state);

        if (st == TASK_INTERRUPTIBLE || st == TASK_UNINTERRUPTIBLE) {
            if (ubuf && total < max) {
                struct sleep_proc sp;
                sp.pid   = task_pid_nr(p);
                sp.tgid  = task_tgid_nr(p);
                sp.state = st;
                memset(sp.comm, 0, SLP_COMM_LEN);
                strncpy(sp.comm, p->comm, SLP_COMM_LEN - 1);

                if (copy_to_user(&ubuf[total], &sp, sizeof(sp))) {
                    rcu_read_unlock();
                    return -EFAULT;
                }
            }
            total++;
        }
    }
    rcu_read_unlock();
    return total;  /* pode ser > max; chame de novo com buffer maior se quiser tudo */
}