
#ifndef _SLEEPLIST_H
#define _SLEEPLIST_H

#define SLP_COMM_LEN 16  /* mesmo de TASK_COMM_LEN */

struct sleep_proc {
    int  pid;                 /* PID */
    int  tgid;                /* TGID */
    long state;               /* 1=S, 2=D (ver <linux/sched.h>) */
    char comm[SLP_COMM_LEN];  /* nome curto */
};

#endif
