/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */
//! Synchronous file output streams used by legacy game save writers.

use super::{ns_string, NSInteger, NSUInteger};
use crate::fs::GuestPath;
use crate::mem::ConstPtr;
use crate::objc::{autorelease, id, objc_classes, ClassExports, HostObject};

struct OutputStreamHostObject {
    path: String,
    append: bool,
    bytes: Vec<u8>,
    opened: bool,
}
impl HostObject for OutputStreamHostObject {}

pub const CLASSES: ClassExports = objc_classes! {

(env, this, _cmd);

@implementation NSStream: NSObject
@end

@implementation NSOutputStream: NSStream

+ (id)outputStreamToFileAtPath:(id)path append:(bool)append {
    let path = ns_string::to_rust_string(env, path).into_owned();
    let stream = OutputStreamHostObject { path, append, bytes: Vec::new(), opened: false };
    let object = env.objc.alloc_object(this, Box::new(stream), &mut env.mem);
    autorelease(env, object)
}

- (())open {
    let stream = env.objc.borrow::<OutputStreamHostObject>(this);
    let path = stream.path.clone();
    let append = stream.append;
    let bytes = if append {
        env.fs.read(GuestPath::new(&path)).unwrap_or_default()
    } else {
        Vec::new()
    };
    let opened = env.fs.write(GuestPath::new(&path), &bytes).is_ok();
    let stream = env.objc.borrow_mut::<OutputStreamHostObject>(this);
    stream.bytes = bytes;
    stream.opened = opened;
}

- (NSInteger)write:(ConstPtr<u8>)buffer maxLength:(NSUInteger)length {
    if !env.objc.borrow::<OutputStreamHostObject>(this).opened {
        return -1;
    }
    let bytes = env.mem.bytes_at(buffer, length).to_vec();
    let stream = env.objc.borrow_mut::<OutputStreamHostObject>(this);
    stream.bytes.extend_from_slice(&bytes);
    let path = stream.path.clone();
    let contents = stream.bytes.clone();
    if env.fs.write(GuestPath::new(&path), &contents).is_err() {
        env.objc.borrow_mut::<OutputStreamHostObject>(this).opened = false;
        return -1;
    }
    length as NSInteger
}

- (())close {
    env.objc.borrow_mut::<OutputStreamHostObject>(this).opened = false;
}

- (bool)hasSpaceAvailable {
    env.objc.borrow::<OutputStreamHostObject>(this).opened
}

- (())dealloc {
    env.objc.dealloc_object(this, &mut env.mem);
}

@end

};
