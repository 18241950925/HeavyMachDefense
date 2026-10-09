/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */
//! `UIAlertView`.

use crate::frameworks::foundation::ns_string;
use crate::objc::{id, msg, msg_super, nil, objc_classes, release, retain, ClassExports};
use crate::Environment;
use std::borrow::Cow;
use std::collections::HashMap;

#[derive(Default)]
pub struct State {
    purchase_alerts: HashMap<id, id>,
    pending_cancellations: Vec<(id, id)>,
}

/// Deliver after the initiating guest method has returned. The original game
/// pauses after calling show, so cancelling synchronously would leave it paused.
pub fn handle_pending(env: &mut Environment) {
    let pending = std::mem::take(&mut env.framework_state.uikit.ui_view.ui_alert_view.pending_cancellations);
    for (alert, delegate) in pending {
        let _: () = msg![env; delegate alertView:alert clickedButtonAtIndex:0i32];
        release(env, delegate);
        release(env, alert);
        log!("Offline purchase cancelled; original game callback delivered");
    }
}

pub const CLASSES: ClassExports = objc_classes! {

(env, this, _cmd);

@implementation UIAlertView: UIView

- (id)initWithTitle:(id)title
                      message:(id)message
                     delegate:(id)delegate
            cancelButtonTitle:(id)cancelButtonTitle
            otherButtonTitles:(id)otherButtonTitles {

    log!("TODO: [(UIAlertView*){:?} initWithTitle:{:?} message:{:?} delegate:{:?} cancelButtonTitle:{:?} otherButtonTitles:{:?}]", this, title, message, delegate, cancelButtonTitle, otherButtonTitles);

    let msg = if message == nil { Cow::from("(nil)") } else { ns_string::to_rust_string(env, message) };
    let title = if title == nil { Cow::from("(nil)") } else { ns_string::to_rust_string(env, title) };
    log!("UIAlertView: title: {:?}, message: {:?}", title, msg);

    let offline_purchase = env.bundle.bundle_identifier() == "com.wemadeent.HeavyMachDefence"
        && title.as_ref() == "Confirm Your In-App Purchase"
        && cancelButtonTitle != nil && delegate != nil;
    let this: id = msg_super![env; this init];
    if offline_purchase {
        env.framework_state.uikit.ui_view.ui_alert_view.purchase_alerts.insert(this, delegate);
    }
    this
}

- (())addButtonWithTitle:(id)title {
    log!("TODO: [(UIAlertView *){:?} addButtonWithTitle:{}]", this, ns_string::to_rust_string(env, title));
}

- (())show {
    if let Some(delegate) = env.framework_state.uikit.ui_view.ui_alert_view.purchase_alerts.remove(&this) {
        retain(env, this);
        retain(env, delegate);
        env.framework_state.uikit.ui_view.ui_alert_view.pending_cancellations.push((this, delegate));
        log!("Original iOS purchase is unavailable in this offline port; scheduling cancellation");
        return;
    }
    log!("TODO: [(UIAlertView*){:?} show]", this);
}

- (())dealloc {
    env.framework_state.uikit.ui_view.ui_alert_view.purchase_alerts.remove(&this);
    msg_super![env; this dealloc]
}

@end

};
