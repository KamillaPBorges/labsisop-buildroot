#ifndef _SLEEPLIST_H
#define _SLEEPLIST_H

#define SLP_COMM_LEN 16  /* igual TASK_COMM_LEN */

struct sleep_proc {
    int  pid;                 /* PID */
    int  tgid;                /* TGID (process group / líder de thread) */
    long state;               /* 1=S, 2=D */
    char comm[SLP_COMM_LEN];  /* nome curto do processo */
};

#endif