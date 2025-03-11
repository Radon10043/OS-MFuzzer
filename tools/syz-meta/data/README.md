Here store the files related to experimental data.


```
data
├── prompts     // Prompts used in the MR identification and calibration
│   ├── calibrator
│   │   ├── system.md
│   │   └── vanilla.md
│   └── identifier
│       ├── follow.md
│       ├── init.md
│       └── system.md
├── README.md   // This file
└── specifications  // Specifications used in MR identificaiton and calibration
    └── linux-v6.2  // Speicfications from linux kernel v6.2
        └── autofs  // Speicfications of driver autofs
            ├── full.md                             // Full specification of autofs
            ├── sec1_purpose.md                     // Content of "Purpose" section in the specification
            ├── sec2_context.md                     // Content of "Context" section in the specification
            ├── sec3_content.md                     // Content of "Content" section in the specification
            ├── sec4_mount_traps.md                 // Content of "Mount Traps" section in the specification
            ├── sec5_mountpoint_expiry.md           // Content of "Mountpoint expiry" section in the specification
            ├── sec6_comm_detecting_the_daemon.md   // Content of "Communicating with autofs: detecting the daemon" section in the specification
            ├── sec7_comm_the_event_pipe.md         // Content of "Communicating with autofs: the event pipe" section in the specification
            ├── sec8_comm_root_directory_ioctls.md  // Content of "Communicating with autofs: root directory ioctls" section in the specification
            ├── sec9_comm_char-device_ioctls.md     // Content of "Communicating with autofs: char-device ioctls" section in the specification
            ├── sec10_catatonic_mode.md             // Content of "Catatonic mode" section in the specification
            ├── sec11_the_ignore_mount_option.md    // Content of "The 'ignore' mount option" section in the specification
            └── sec12_autofs_name_spaces_etc.md     // Content of "autofs, name spaces, and shared mounts" section in the specification
```

Source of specifications:

- data/specifications/linux-v6.2: https://www.kernel.org/doc/html/v6.2/index.html
- data/specifications/linux-v6.2/autofs: https://www.kernel.org/doc/html/v6.2/filesystems/autofs.html