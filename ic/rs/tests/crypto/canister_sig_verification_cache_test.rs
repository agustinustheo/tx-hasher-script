#[rustfmt::skip]

use anyhow::Result;

use ic_tests::canister_sig_verification_cache_test::{config, test};
use ic_tests::driver::group::SystemTestGroup;
use ic_tests::systest;

fn main() -> Result<()> {
    SystemTestGroup::new()
        .with_setup(config)
        .add_test(systest!(test))
        .execute_from_args()?;

    Ok(())
}
